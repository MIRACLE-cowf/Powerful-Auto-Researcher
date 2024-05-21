import operator
from typing import Literal, TypedDict, Annotated, Union

from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.pydantic_v1 import BaseModel, Field
from langgraph.graph import StateGraph

from Agent_Team.Member.Common_Search_AgentGraph import TavilySearchAgentGraph, BraveSearchAgentGraph, WikipediaSearchAgentGraph, YoutubeSearchAgentGraph, ArxivSearchAgentGraph
from Agent_Team.Member.PAR_Document_Writer import get_document_generation_agent
from CustomHelper.Anthropic_helper import format_to_anthropic_tool_messages
from CustomHelper.Custom_AnthropicAgentOutputParser_2 import AnthropicAgentOutputParser
from CustomHelper.Helper import retry_with_delay_async
from CustomHelper.load_model import get_anthropic_model
from Util.PAR_Helper import extract_result

members = ["tavily_agent", "document_agent", "wikipedia_agent", "youtube_agent", "arxiv_agent", "brave_agent"]


class route(BaseModel):
    """Select the next agent ONLY ONE.
    Remember the next agent can't access provided section. So you MUST provide specific and clear instructions to next agent."""
    next: Literal[
        "tavily_agent", "document_agent", "wikipedia_agent", "youtube_agent", "arxiv_agent", "brave_agent", "FINISH"] = Field(...,
                                                                                                               description="Select the next agent ONLY ONE or 'FINISH'. 'FINISH' means you are team finish all job and ready to return result.")
    instructions: str = Field(...,
                              description="Provide specific, clear, and detailed instructions that next agent what should do.")


def _get_PM_agent():
    PM_Prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a perfect project manager agent who has successfully led projects by providing clear instructions to team members over a long period.

Currently, you have been assigned to handle a part of the "PAR" project, which involves writing a Markdown document.

You will be given high-level information corresponding to a specific section of the entire document.
Your task is to write clear and precise instructions to agents specialized in each search engine and the agent writing the document, in order to create perfect content for given section.

Each team member will proceed with their work based solely on your instructions, so it is crucial to write clear and precise instructions.

<instructions>
1. Thoroughly analyze the high-level information about the section to identify the necessary search engines and queries.

2. Provide clear guidelines and specific search requests to the designated search agent.
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
- When selecting a team member, use only the provided 'route' tool. You must call only one agent at a time, and parallel selection is not currently available.
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


def transform_search_result(search_engine: str, search_result: str) -> str:
    return f"<{search_engine}_search_result>\n{search_result}\n</{search_engine}_search_result>"


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

    if isinstance(pm_result, list) and len(pm_result) > 0:
        _next = pm_result[0].tool_input["next"]
        print(f"Next is {_next}")

        if 'human' in _next or 'FINISH' in _next:
            return {
                "agent_output": pm_result[0],
                "next": "FINISH",
                "final_section_document": state["final_section_document"],
            }

        return {
            "agent_output": pm_result[0],
            "next": pm_result[0].tool_input["next"],
            "instructions": pm_result[0].tool_input["instructions"],
        }
    elif isinstance(pm_result, AgentFinish):
        return {
            "agent_output": pm_result,
            "next": "FINISH",
            "final_section_document": state["final_section_document"],
        }
    else:
        raise ValueError(f"Unexpected agent output: {pm_result}, type: {type(pm_result)}")


async def tavily_agent_node(state: AgentState) -> dict:
    PAR_Team_Member_Agent_Tavily = TavilySearchAgentGraph()
    print(f"---{state['order']} PM AGENT CALLED TAVILY AGENT---")
    messages = HumanMessage(content=f"Hi! I'm PAR Project Manager Agent! {state['instructions']}")
    tavily_agent_result = await PAR_Team_Member_Agent_Tavily.get_search_agent_graph().ainvoke({"input": messages.content, "section_basic_info": state["section_basic_info"]})
    extract_tavily_agent_result = extract_result(tavily_agent_result["agent_outcome"].return_values["output"])
    tavily_search_result = transform_search_result(search_engine="Tavily", search_result=extract_tavily_agent_result)
    return {
        "intermediate_steps": [(state["agent_output"], extract_tavily_agent_result)],
        "search_result": state["search_result"] + "\n\n" + tavily_search_result
    }


async def brave_agent_node(state: AgentState) -> dict:
    PAR_Team_Member_Agent_Brave = BraveSearchAgentGraph()
    print(f"---{state['order']} PM AGENT CALLED BRAVE AGENT---")
    messages = HumanMessage(content=f"Hi! I'm PAR Project Manager Agent! {state['instructions']}")
    brave_agent_result = await PAR_Team_Member_Agent_Brave.get_search_agent_graph().ainvoke({"input": messages.content, "section_basic_info": state["section_basic_info"]})
    extract_brave_agent_result = extract_result(brave_agent_result["agent_outcome"].return_values["output"])
    brave_search_result = transform_search_result(search_engine="BraveSearch", search_result=extract_brave_agent_result)
    return {
        "intermediate_steps": [(state["agent_output"], extract_brave_agent_result)],
        "search_result": state["search_result"] + "\n\n" + brave_search_result
    }


async def wikipedia_agent_node(state: AgentState) -> dict:
    PAR_Team_Member_Agent_Wikipedia = WikipediaSearchAgentGraph()
    print(f"---{state['order']} PM AGENT CALLED WIKIPEDIA AGENT---")
    messages = HumanMessage(content=f"Hi! I'm PAR Project Manager Agent! {state['instructions']}")
    wikipedia_agent_result = await PAR_Team_Member_Agent_Wikipedia.get_search_agent_graph().ainvoke({"input": messages.content, "section_basic_info": state["section_basic_info"]})
    extract_wikipedia_agent_result = extract_result(wikipedia_agent_result["agent_outcome"].return_values["output"])
    wikipedia_search_result = transform_search_result(search_engine="Wikipedia",
                                                      search_result=extract_wikipedia_agent_result)
    return {
        "intermediate_steps": [(state["agent_output"], extract_wikipedia_agent_result)],
        "search_result": state["search_result"] + "\n\n" + wikipedia_search_result
    }


async def youtube_agent_node(state: AgentState) -> dict:
    PAR_Team_Member_Agent_Youtube = YoutubeSearchAgentGraph()
    print(f"---{state['order']} PM AGENT CALLED YOUTUBE AGENT---")
    messages = HumanMessage(content=f"Hi! I'm PAR Project Manager Agent! {state['instructions']}")
    youtube_agent_result = await PAR_Team_Member_Agent_Youtube.get_search_agent_graph().ainvoke({"input": messages.content, "section_basic_info": state["section_basic_info"]})
    extract_youtube_agent_result = extract_result(youtube_agent_result["agent_outcome"].return_values["output"])
    youtube_search_result = transform_search_result(search_engine="Youtube", search_result=extract_youtube_agent_result)
    return {
        "intermediate_steps": [(state["agent_output"], extract_youtube_agent_result)],
        "search_result": state["search_result"] + "\n\n" + youtube_search_result
    }


async def arXiv_agent_node(state: AgentState) -> dict:
    PAR_Team_Member_Agent_ArXiv = ArxivSearchAgentGraph()
    print(f"---{state['order']} PM AGENT CALLED ARXIV AGENT---")
    messages = HumanMessage(content=f"Hi! I'm PAR Project Manager Agent! {state['instructions']}")
    arxiv_agent_result = await PAR_Team_Member_Agent_ArXiv.get_search_agent_graph().ainvoke({"input": messages.content, "section_basic_info": state["section_basic_info"]})
    extract_arxiv_agent_result = extract_result(arxiv_agent_result["agent_outcome"].return_values["output"])
    arxiv_search_result = transform_search_result(search_engine="ArXiv", search_result=extract_arxiv_agent_result)
    return {
        "intermediate_steps": [(state["agent_output"], extract_arxiv_agent_result)],
        "search_result": state["search_result"] + "\n\n" + arxiv_search_result
    }


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
    workflow.add_node("response", response_node)

    for member in members:
        workflow.add_edge(member, "manager")

    conditional_map = {k: k for k in members}
    conditional_map["FINISH"] = "response"
    workflow.add_conditional_edges("manager", lambda x: x["next"], conditional_map)
    workflow.set_entry_point("manager")
    workflow.set_finish_point("response")
    project_manager_graph = workflow.compile().with_config(run_name="Project Manager Agent")

    return project_manager_graph


def get_pm_graph_mermaid():
    app = get_pm_graph()
    print("Project Manager Agent Graph Mermaid")
    print(app.get_graph().draw_mermaid())