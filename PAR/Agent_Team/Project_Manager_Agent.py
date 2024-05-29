import operator
from typing import Literal, TypedDict, Annotated, Union, Any

from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.runnables import Runnable
from langgraph.graph import StateGraph
from langsmith import traceable

from Agent_Team.Member.Common_Search_AgentGraph import TavilySearchAgentGraph, BraveSearchAgentGraph, WikipediaSearchAgentGraph, YoutubeSearchAgentGraph, ArxivSearchAgentGraph, AskNewsSearchAgentGraph
from Agent_Team.Member.PAR_Document_Writer import get_document_generation_agent
from CustomHelper.Anthropic_helper import format_to_anthropic_tool_messages
from CustomHelper.Custom_AnthropicAgentOutputParser_2 import AnthropicAgentOutputParser
from CustomHelper.Helper import retry_with_delay_async
from CustomHelper.load_model import get_anthropic_model
from Util.PAR_Helper import extract_result

members = ["tavily_agent", "document_agent", "wikipedia_agent", "youtube_agent", "arxiv_agent", "brave_agent", "asknews_agent"]


class route(BaseModel):
    """Select the next agent ONLY ONE that perform action.
    Remember the next agent can't access provided section. So you MUST provide specific and clear instructions to the next agent."""
    next: Literal[
        "tavily_agent",
        "document_agent",
        "wikipedia_agent",
        "youtube_agent",
        "arxiv_agent",
        "brave_agent",
        "asknews_agent",
        "FINISH",
    ] = Field(..., description="Select the next agent ONLY ONE that perform action or 'FINISH'. 'FINISH' means you are team finish all job and ready to return result.")
    instructions: str = Field(...,
                              description="Provide specific, clear, and detailed instructions that the selected agent what should do.")


def _get_PM_agent():
    PM_Prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a perfect project manager agent who has successfully led projects by providing clear instructions to team members over a long period.

Currently, you have been assigned to handle a part of the "PAR" project, which involves writing a Markdown document.

You will be given high-level information corresponding to a specific section of the entire document.
Your task is to write clear and precise instructions to agents specialized in each search engine and the agent writing the document, in order to create perfect content for given section.

Each team member will proceed with their work based solely on your instructions, so it is crucial to write clear and precise instructions.

<team_members>
You will be working with the following team members:

- tavily_agent: Specialized search agent using Tavily API
- document_agent: Responsible for writing the document
- wikipedia_agent: Specialized search agent for Wikipedia
- youtube_agent: Specialized search agent for YouTube
- arxiv_agent: Specialized search agent for arXiv
- brave_agent: Specialized search agent using Brave Search API
- asknews_agent: Specialized search agent for News using AskNews API

Note that only the document_agent is responsible for writing the document, while all other agents are specialized in conducting searches.
</team_members>

<instructions>
1. Thoroughly analyze the high-level information about the section to identify the necessary search engines and queries.

2. Provide clear instruction and specific search requests to the designated search agent using 'route' tool.
- Each search agent will return results selected based on strict 'search evaluation criteria'.
- If the results are insufficient, provide detailed feedback to the agent and write instructions requesting additional searches.

3. Once sufficient high-quality information has been collected for the section, call the 'document generation' agent. Again, write clear and precise instructions to deliver to them.

4. The 'document generation' agent will also return a final document evaluated according to strict guidelines, but you will review it once more.

5. If the final document is perfect for the section, use 'FINISH' to deliver it to the user.
</instructions>

<restrictions>
- Each team member agent is unaware of your current situation.
- Each team member agent is unaware of the high-level information about the section.
- Each team member agent does not share what results they have returned with each other and has no information about it.
- So, Each team member agent will proceed with their work based solely on your instructions, so write clear and precise instructions.
- Maintain smooth and respectful interactions among team member agents.
- When selecting a team member, use only the provided 'route' tool. 
- When using 'route' tool, you must call ONLY ONE agent at a time, and parallel selection is NOT currently available.
- The 'search' agents are specialized only in searching, so they are not suitable for tasks such as reviews or evaluations.
- Use 'FINISH' through 'route' only when delivering the final document to the user.
</restrictions>


As the Project Manager Agent, strive to coordinate your team members effectively to create a high-quality section of the document."""),
        ("human", "<section_information>\n{input}\n</section_information>"),
        MessagesPlaceholder(variable_name="agent_scratchpad")
    ])

    PM_llm = get_anthropic_model(model_name="sonnet")

    PM_chain = (
            {
                "input"           : lambda x: x["input"],
                "agent_scratchpad": lambda x: format_to_anthropic_tool_messages(x["intermediate_steps"])
            }
            | PM_Prompt
            | PM_llm.bind_tools(tools=[route], tool_choice="route").with_fallbacks([PM_llm.bind_tools(tools=[route], tool_choice="route")] * 3)
            | AnthropicAgentOutputParser()
    )
    return PM_chain


class AgentState(TypedDict):
    order: int
    input: str
    section_basic_info: str
    agent_output: Union[AgentAction, AgentFinish, None]
    intermediate_steps: Annotated[list[tuple[AgentAction, str]], operator.add]
    next: str
    instructions: str
    search_result: str
    final_section_document: str


def _transform_search_result(search_engine: str, search_result: str) -> str:
    return f"<{search_engine}_search_result>\n{search_result}\n</{search_engine}_search_result>"


def _check_pm_agent_result(_pm_result: Any, _final_section_document: str):
    if isinstance(_pm_result, list) and len(_pm_result) > 0:
        _next = _pm_result[0].tool_input["next"]
        print(f"Next is {_next}, type is {type(_next)}")

        if isinstance(_next, list):
            if len(_next) > 1:
                _next = _next[0]
            else:
                _next = _pm_result[0].tool_input["next"]
        elif isinstance(_next, str) and ',' in _next:
            _next = _next.split(',')[0].strip()

        if 'human' in _next or 'FINISH' in _next:
            return {
                "agent_output": _pm_result[0],
                "next": "FINISH",
                "final_section_document": _final_section_document,
            }

        return {
            "agent_output": _pm_result[0],
            "next": _next,
            "instructions": _pm_result[0].tool_input["instructions"],
        }
    elif isinstance(_pm_result, AgentFinish):
        return {
            "agent_output": _pm_result,
            "next": "FINISH",
            "final_section_document": _final_section_document,
        }
    else:
        raise ValueError(f"Unexpected agent output: {_pm_result}, type: {type(_pm_result)}")


async def _run_search_agent(
    state: AgentState,
    search_agent: Runnable,
    search_engine: str,
) -> dict:
    print(f"---{state['order']} PM AGENT CALLED {search_engine.upper()} AGENT---")
    messages = HumanMessage(content=f"Hi! I'm PAR Project Manager Agent! {state['instructions']}")
    try:
        agent_result = await search_agent.ainvoke({"input": messages.content, "section_basic_info": state["section_basic_info"]}, {'recursion_limit': 100})
        extract_agent_result = extract_result(agent_result["agent_outcome"].return_values["output"])
        search_result = _transform_search_result(search_engine=search_engine, search_result=extract_agent_result)
        return {
            "intermediate_steps": [(state["agent_output"], extract_agent_result)],
            "search_result"     : state["search_result"] + "\n\n" + search_result
        }
    except Exception as e:
        print(f"Error Occur at '{search_engine.lower()} agent node'. Detail: {str(e)}")
        print(f"{search_engine} agent result: {agent_result}")
        raise Exception(e)


@traceable(name="Run PM Agent", run_type="llm")
async def run_pm_agent(state: AgentState) -> dict:
    print("### PM AGENT RUN ###")
    PM_chain = _get_PM_agent()
    pm_result = await retry_with_delay_async(
        chain=PM_chain,
        input={
            "input": state["input"],
            "intermediate_steps": state["intermediate_steps"],
        },
        max_retries=5,
        delay_seconds=45.0
    )
    return _check_pm_agent_result(
        _pm_result=pm_result,
        _final_section_document=state["final_section_document"]
    )


@traceable(name="AskNews Agent")
async def asknews_agent_node(state: AgentState) -> dict:
    PAR_Team_Member_Agent_AskNews = AskNewsSearchAgentGraph()
    return await _run_search_agent(state, PAR_Team_Member_Agent_AskNews.get_search_agent_graph(), "AskNews")


@traceable(name="Tavily Agent")
async def tavily_agent_node(state: AgentState) -> dict:
    PAR_Team_Member_Agent_Tavily = TavilySearchAgentGraph()
    return await _run_search_agent(state, PAR_Team_Member_Agent_Tavily.get_search_agent_graph(), "Tavily")


@traceable(name="Brave Agent")
async def brave_agent_node(state: AgentState) -> dict:
    PAR_Team_Member_Agent_Brave = BraveSearchAgentGraph()
    return await _run_search_agent(state, PAR_Team_Member_Agent_Brave.get_search_agent_graph(), "BraveSearch")


@traceable(name="Wikipedia Agent")
async def wikipedia_agent_node(state: AgentState) -> dict:
    PAR_Team_Member_Agent_Wikipedia = WikipediaSearchAgentGraph()
    return await _run_search_agent(state, PAR_Team_Member_Agent_Wikipedia.get_search_agent_graph(), "Wikipedia")


@traceable(name="YouTube Agent")
async def youtube_agent_node(state: AgentState) -> dict:
    PAR_Team_Member_Agent_Youtube = YoutubeSearchAgentGraph()
    return await _run_search_agent(state, PAR_Team_Member_Agent_Youtube.get_search_agent_graph(), "Youtube")


@traceable(name="Arxiv Agent")
async def arXiv_agent_node(state: AgentState) -> dict:
    PAR_Team_Member_Agent_ArXiv = ArxivSearchAgentGraph()
    return await _run_search_agent(state, PAR_Team_Member_Agent_ArXiv.get_search_agent_graph(), "ArXiv")


@traceable(name="Document Generate Agent", run_type="llm")
async def document_agent_node(state: AgentState) -> dict:
    Document_Writer_chain = get_document_generation_agent()
    print(f"---{state['order']} PM AGENT CALLED DOCUMENT GENERATOR AGENT---")
    messages = HumanMessage(content=f"Hi! I'm PAR Project Manager Agent! {state['instructions']}")
    document_agent_result = await retry_with_delay_async(
        chain=Document_Writer_chain,
        input={
            "input": messages.content,
            "section_info": state["section_basic_info"],
            "search_results": state["search_result"]
        },
        max_retries=5,
        delay_seconds=60.0
    )
    return {
        "final_section_document": document_agent_result,
        "intermediate_steps": [(state["agent_output"], document_agent_result)],
    }


def response_node(state: AgentState) -> dict:
    print(f"### {state['order']} PM AGENT DONE ALL WORK ###")
    return {
        "agent_output": state["agent_output"],
        "final_section_document": state["final_section_document"],
        "order": state["order"],
    }


def get_pm_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("manager", run_pm_agent)
    workflow.add_node("tavily_agent", tavily_agent_node)
    workflow.add_node("brave_agent", brave_agent_node)
    workflow.add_node("document_agent", document_agent_node)
    workflow.add_node("wikipedia_agent", wikipedia_agent_node)
    workflow.add_node("youtube_agent", youtube_agent_node)
    workflow.add_node("arxiv_agent", arXiv_agent_node)
    workflow.add_node("asknews_agent", asknews_agent_node)
    workflow.add_node("response", response_node)

    for member in members:
        workflow.add_edge(member, "manager")

    conditional_map = {k: k for k in members}
    conditional_map["FINISH"] = "response"
    workflow.add_conditional_edges("manager", lambda x: x["next"], conditional_map)
    workflow.set_entry_point("manager")
    workflow.set_finish_point("response")
    project_manager_graph = workflow.compile()

    return project_manager_graph


def get_pm_graph_mermaid():
    app = get_pm_graph()
    print("Project Manager Agent Graph Mermaid")
    print(app.get_graph().draw_mermaid())