import operator
from typing import TypedDict, Union, Annotated, Dict, Any

from langchain_core.agents import AgentAction, AgentFinish
from langgraph.graph import StateGraph, END

from Agent_Team.create_agent import create_agent
from CustomHelper.Agent_outcome_checker import agent_outcome_checker
from CustomHelper.load_model import get_anthropic_model
from Tool.CustomTavilySearchFunc import tavily_search_func
from Tool.Custom_TavilySearchResults import Custom_TavilySearchResults


class AgentState(TypedDict):
    agent_outcome: Union[AgentAction, AgentFinish, None]
    intermediate_steps: Annotated[list[tuple[AgentAction, str]], operator.add]
    keys: Dict[str, Any]
    input: str


tavilytools = Custom_TavilySearchResults()


def run_agent(data: AgentState):
    print('---TAVILY AGENT GRAPH RUN---')
    input = data["input"]
    intermediate_steps = data["intermediate_steps"]
    agent = create_agent(llm=get_anthropic_model(model_name="sonnet"), tool=tavilytools, agent_specific_role="Tavily")
    return agent_outcome_checker(agent=agent, input=input, intermediate_steps=intermediate_steps)


def router(data: AgentState):
    print('---TAVILY AGENT GRAPH ROUTER---')
    if isinstance(data['agent_outcome'], AgentFinish):
        return 'end'
    else:
        return 'tavily'


def tavily_node(data: AgentState):
    print('---TAVILY AGENT GRAPH TAVIL API---')
    agent_action = data['agent_outcome']
    result = tavily_search_func(
        query=agent_action.tool_input['query'],
        max_results=agent_action.tool_input['max_results']
    )
    return {
        'intermediate_steps': [(agent_action, result)]
    }


def get_tavily_search_agent_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("agent", run_agent)
    workflow.add_node("tavily", tavily_node)
    workflow.add_conditional_edges(
        "agent",
        router,
        {
            "end"   : END,
            "tavily": "tavily"
        }
    )
    workflow.add_edge("tavily", "agent")
    workflow.set_entry_point("agent")
    PAR_Team_Member_Agent_Tavily = workflow.compile().with_config(run_name="PAR_Team_Member_Agent_Tavily")
    return PAR_Team_Member_Agent_Tavily


def get_tavily_search_agent_graph_mermaid():
    app = get_tavily_search_agent_graph()
    print(app.get_graph().draw_mermaid())

