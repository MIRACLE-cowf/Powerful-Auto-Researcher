import operator
from typing import TypedDict, Union, Annotated, Dict, Sequence

from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, END

from Agent_Team.create_agent import create_agent
from CustomHelper.load_model import get_anthropic_model
from Tool.CustomSearchFunc import web_search
from Tool.CustomSearchFunc_v2 import web_search_v2
from Util.Retriever_setup import mongodb_store, parent_retriever


class AgentState(TypedDict):
    agent_outcome: Union[AgentAction, AgentFinish, None]
    intermediate_steps: Annotated[list[tuple[AgentAction, str]], operator.add]
    keys: Dict[str, any]
    input: str


tavilytools = TavilySearchResults()


def run_agent(data):
    print(f"TAVILY RUN AGENT: {data}")
    input = data["input"]
    intermediate_steps = data["intermediate_steps"]
    agent = create_agent(llm=get_anthropic_model(), tools=[tavilytools], agent_specific_role="Tavily")
    agent_outcome = agent.invoke({"input": input, "intermediate_steps": intermediate_steps})

    if isinstance(agent_outcome, list) and len(agent_outcome) > 0:
        return {"agent_outcome": agent_outcome[0]}
    elif isinstance(agent_outcome, AgentFinish):
        return {"agent_outcome": agent_outcome}
    else:
        raise ValueError(f"Unexpected agent_outcome: {agent_outcome}")


def router(data):
    print('---ROUTER---')
    if isinstance(data['agent_outcome'], AgentFinish):
        return 'end'
    else:
        return 'tavily'


def tavily_node(data):
    print('---TAVIL---')
    agent_action = data['agent_outcome']
    print(agent_action)
    result = web_search_v2(
        query=agent_action.tool_input['query'],
    )
    return {
        'intermediate_steps': [(agent_action, result)]
    }


workflow = StateGraph(AgentState)
workflow.add_node("agent", run_agent)
workflow.add_node("tavily", tavily_node)
workflow.add_conditional_edges(
    "agent",
    router,
    {
        "end": END,
        "tavily": "tavily"
    }
)
workflow.add_edge("tavily", "agent")
workflow.set_entry_point("agent")
PAR_Team_Member_Agent_Tavily = workflow.compile().with_config(run_name="PAR_Team_Member_Agent_Tavily")
