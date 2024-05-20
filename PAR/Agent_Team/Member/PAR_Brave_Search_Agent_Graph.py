import operator
from typing import TypedDict, Union, Annotated, Dict, Any

from langchain_core.agents import AgentAction, AgentFinish
from langgraph.graph import StateGraph, END

from Agent_Team.create_agent import create_agent
from CustomHelper.Agent_outcome_checker import agent_outcome_checker
from CustomHelper.load_model import get_anthropic_model
from Tool.CustomBraveSearchFunc import brave_search_func
from Tool.Custom_BraveSearchResults import Custom_BraveSearchResults


class AgentState(TypedDict):
    agent_outcome: Union[AgentAction, AgentFinish, None]
    intermediate_steps: Annotated[list[tuple[AgentAction, str]], operator.add]
    keys: Dict[str, Any]
    input: str


bravetools = Custom_BraveSearchResults()


def run_agent(data: AgentState):
    print('---BRAVE AGENT GRAPH RUN---')
    input = data["input"]
    intermediate_steps = data["intermediate_steps"]
    agent = create_agent(llm=get_anthropic_model(model_name="sonnet"), tool=bravetools, agent_specific_role="Tavily")
    return agent_outcome_checker(agent=agent, input=input, intermediate_steps=intermediate_steps)


def router(data: AgentState):
    print('---BRAVE AGENT GRAPH ROUTER---')
    if isinstance(data['agent_outcome'], AgentFinish):
        return 'end'
    else:
        return 'brave'


def brave_node(data: AgentState):
    print('---BRAVE AGENT GRAPH BRAVE API---')
    agent_action = data['agent_outcome']
    result = brave_search_func(
        query=agent_action.tool_input['query'],
        max_results=agent_action.tool_input['max_results']
    )
    return {
        'intermediate_steps': [(agent_action, result)]
    }


def get_brave_search_agent_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("agent", run_agent)
    workflow.add_node("brave", brave_node)
    workflow.add_conditional_edges(
        "agent",
        router,
        {
            "end"  : END,
            "brave": "brave"
        }
    )
    workflow.add_edge("brave", "agent")
    workflow.set_entry_point("agent")
    PAR_Team_Member_Agent_Brave = workflow.compile().with_config(run_name="PAR_Team_Member_Agent_Brave")
    return PAR_Team_Member_Agent_Brave


def get_brave_search_agent_graph_mermaid():
    app = get_brave_search_agent_graph()
    print(app.get_graph().draw_mermaid())
