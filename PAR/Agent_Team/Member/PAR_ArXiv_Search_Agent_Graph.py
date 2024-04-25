import operator
from typing import TypedDict, Union, Annotated, Dict

from langchain_core.agents import AgentAction, AgentFinish
from langgraph.graph import StateGraph, END

from Agent_Team.create_agent import create_agent
from CustomHelper.Agent_outcome_checker import agent_outcome_checker
from CustomHelper.load_model import get_anthropic_model
from Tool.CustomSearchFunc_v2 import arxiv_search_v2
from Tool.CustomSearchTool import Custom_arXivSearchTool


class AgentState(TypedDict):
    agent_outcome: Union[AgentAction, AgentFinish, None]
    intermediate_steps: Annotated[list[tuple[AgentAction, str]], operator.add]
    keys: Dict[str, any]
    input: str


arXiv_search_tool = Custom_arXivSearchTool()


def run_agent(data):
    print(">>>> ARXIV AGENT RUN <<<<")
    input = data["input"]
    intermediate_steps = data["intermediate_steps"]
    agent = create_agent(llm=get_anthropic_model(), tools=[arXiv_search_tool], agent_specific_role="ArXiv")
    return agent_outcome_checker(agent=agent, input=input, intermediate_steps=intermediate_steps)


def router(data):
    print('>>>> ARXIV AGENT ROUTER <<<<')
    if isinstance(data['agent_outcome'], AgentFinish):
        return 'end'
    else:
        return 'arxiv'


def arXiv_node(data):
    print('>>>> ARXIV AGENT SEARCH <<<<')
    agent_action = data['agent_outcome']
    result = arxiv_search_v2(query=agent_action.tool_input['query'])
    return {
        'intermediate_steps': [(agent_action, result)]
    }


workflow = StateGraph(AgentState)
workflow.add_node("agent", run_agent)
workflow.add_node("arxiv", arXiv_node)
workflow.add_conditional_edges(
    "agent",
    router,
    {
        "end": END,
        "arxiv": "arxiv"
    }
)
workflow.add_edge("arxiv", "agent")
workflow.set_entry_point("agent")
PAR_Team_Member_Agent_ArXiv = workflow.compile().with_config(run_name="PAR_Team_Member_Agent_Arxiv")
