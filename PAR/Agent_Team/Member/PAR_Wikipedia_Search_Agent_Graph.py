import operator
from typing import TypedDict, Union, Annotated, Dict, Sequence

from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.utilities.wikipedia import WikipediaAPIWrapper
from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, END

from Agent_Team.create_agent import create_agent
from CustomHelper.load_model import get_anthropic_model
from Tool.CustomSearchFunc import web_search, wikipedia_search
from Tool.CustomSearchTool import Custom_WikipediaQueryRun
from Util.Retriever_setup import mongodb_store, parent_retriever


class AgentState(TypedDict):
    agent_outcome: Union[AgentAction, AgentFinish, None]
    intermediate_steps: Annotated[list[tuple[AgentAction, str]], operator.add]
    keys: Dict[str, any]
    input: str


wikipedia = Custom_WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper())


def run_agent(data):
    print(">>>> WIKIPEDIA AGENT RUN <<<<")
    input = data["input"]
    intermediate_steps = data["intermediate_steps"]
    agent = create_agent(llm=get_anthropic_model(), tools=[wikipedia], agent_specific_role="Wikipedia")
    agent_outcome = agent.invoke({"input": input, "intermediate_steps": intermediate_steps})

    if isinstance(agent_outcome, list) and len(agent_outcome) > 0:
        return {"agent_outcome": agent_outcome[0]}
    elif isinstance(agent_outcome, AgentFinish):
        return {"agent_outcome": agent_outcome}
    else:
        raise ValueError(f"Unexpected agent_outcome: {agent_outcome}")


def router(data):
    print('>>>> WIKIPEDIA AGENT ROUTER <<<<')
    if isinstance(data['agent_outcome'], AgentFinish):
        return 'end'
    else:
        return 'wikipedia'


def wikipedia_node(data):
    print('>>>> WIKIPEDIA AGENT SEARCH <<<<')
    agent_action = data['agent_outcome']
    result = wikipedia_search(query=agent_action.tool_input['query'])
    return {
        'intermediate_steps': [(agent_action, result)]
    }


workflow = StateGraph(AgentState)
workflow.add_node("agent", run_agent)
workflow.add_node("wikipedia", wikipedia_node)
workflow.add_conditional_edges(
    "agent",
    router,
    {
        "end": END,
        "wikipedia": "wikipedia"
    }
)
workflow.add_edge("wikipedia", "agent")
workflow.set_entry_point("agent")
PAR_Team_Member_Agent_Wikipedia = workflow.compile().with_config(run_name="PAR_Team_Member_Agent_Wikipedia")
