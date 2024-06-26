import operator
from typing import TypedDict, Union, Annotated, Dict, Any

from langchain_community.utilities.wikipedia import WikipediaAPIWrapper
from langchain_core.agents import AgentAction, AgentFinish
from langgraph.graph import StateGraph, END

from Agent_Team.create_agent import create_agent
from CustomHelper.Agent_outcome_checker import agent_outcome_checker
from CustomHelper.load_model import get_anthropic_model
from Tool.CustomSearchFunc import wikipedia_search
from Tool.CustomSearchTool import Custom_WikipediaQueryRun


class AgentState(TypedDict):
    agent_outcome: Union[AgentAction, AgentFinish, None]
    intermediate_steps: Annotated[list[tuple[AgentAction, str]], operator.add]
    keys: Dict[str, Any]
    input: str


wikipedia = Custom_WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper())


def run_agent(data: AgentState):
    print('---WIKIPEDIA AGENT GRAPH RUN---')
    input = data["input"]
    intermediate_steps = data["intermediate_steps"]
    agent = create_agent(llm=get_anthropic_model(), tool=wikipedia, agent_specific_role="Wikipedia")
    return agent_outcome_checker(agent=agent, input=input, intermediate_steps=intermediate_steps)


def router(data: AgentState):
    print('---WIKIPEDIA AGENT GRAPH ROUTER---')
    if isinstance(data['agent_outcome'], AgentFinish):
        return 'end'
    else:
        return 'wikipedia'


def wikipedia_node(data: AgentState):
    print('---WIKIPEDIA AGENT GRAPH WIKIPEDIA API---')
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
