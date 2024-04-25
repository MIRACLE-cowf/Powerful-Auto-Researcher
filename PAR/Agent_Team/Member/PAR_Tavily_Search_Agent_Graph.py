import operator
from typing import TypedDict, Union, Annotated, Dict

from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.agents import AgentAction, AgentFinish
from langgraph.graph import StateGraph, END

from Agent_Team.create_agent import create_agent
from CustomHelper.Agent_outcome_checker import agent_outcome_checker
from CustomHelper.load_model import get_anthropic_model
from Tool.CustomSearchFunc_v2 import web_search_v2


class AgentState(TypedDict):
    agent_outcome: Union[AgentAction, AgentFinish, None]
    intermediate_steps: Annotated[list[tuple[AgentAction, str]], operator.add]
    keys: Dict[str, any]
    input: str


tavilytools = TavilySearchResults()


def run_agent(data):
    print(">>>> TAVILY AGENT RUN <<<<")
    input = data["input"]
    intermediate_steps = data["intermediate_steps"]
    agent = create_agent(llm=get_anthropic_model(model_name="sonnet"), tools=[tavilytools], agent_specific_role="Tavily")
    return agent_outcome_checker(agent=agent, input=input, intermediate_steps=intermediate_steps)


def router(data):
    print('>>>> TAVILY AGENT ROUTER <<<<')
    if isinstance(data['agent_outcome'], AgentFinish):
        return 'end'
    else:
        return 'tavily'


def tavily_node(data):
    print('>>>> TAVILY AGENT SEARCH <<<<')
    agent_action = data['agent_outcome']
    result = web_search_v2(
        query=agent_action.tool_input['query'],
        max_results=agent_action.tool_input['max_results'],
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
