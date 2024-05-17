import operator
from typing import TypedDict, Union, Annotated, Dict, Any

from langchain_community.utilities import WikipediaAPIWrapper
from langchain_core.agents import AgentAction, AgentFinish
from langgraph.graph import StateGraph

from Agent_Team.create_agent import create_agent
from CustomHelper.Agent_outcome_checker import agent_outcome_checker
from CustomHelper.load_model import get_anthropic_model
from Tool.CustomBraveSearchFunc import brave_search_func
from Tool.CustomSearchFunc import wikipedia_search
from Tool.CustomSearchFunc_v2 import arxiv_search_v2, youtube_search_v2
from Tool.CustomSearchTool import Custom_arXivSearchTool, Custom_WikipediaQueryRun, Custom_YouTubeSearchTool
from Tool.CustomTavilySearchFunc import tavily_search_func
from Tool.Custom_BraveSearchResults import Custom_BraveSearchResults
from Tool.Custom_TavilySearchResults import Custom_TavilySearchResults


class AgentState(TypedDict):
	agent_outcome: Union[AgentAction, AgentFinish, None]
	intermediate_steps: Annotated[list[tuple[AgentAction, str]], operator.add]
	keys: Dict[str, Any]
	input: str


class SearchAgentGraph:
	def __init__(self, tool, agent_specific_role):
		self.search_func = None
		self.tool = tool
		self.agent_specific_role = agent_specific_role

	async def __run_agent(self, data: AgentState):
		input = data["input"]
		intermediate_steps = data["intermediate_steps"]
		agent = create_agent(llm=get_anthropic_model(model_name="sonnet"), tools=[self.tool], agent_specific_role=self.agent_specific_role)
		return await agent_outcome_checker(agent=agent, input=input, intermediate_steps=intermediate_steps)

	def __router(self, data: AgentState):
		if isinstance(data["agent_outcome"], AgentFinish):
			return 'end'
		else:
			return self.agent_specific_role.lower()

	async def __search_node(self, data: AgentState):
		agent_action = data['agent_outcome']
		max_results = agent_action.tool_input.get('max_results', None)
		search_result = await self.search_func(
			query=agent_action.tool_input['query'],
			max_results=max_results
		)
		return {
			'intermediate_steps': [(agent_action, search_result)]
		}

	def get_search_agent_graph(self):
		workflow = StateGraph(AgentState)
		workflow.add_node("agent", self.__run_agent)
		workflow.add_node(self.agent_specific_role.lower(), self.__search_node)
		from langgraph.graph import END
		workflow.add_conditional_edges(
			"agent",
			self.__router,
			{
				"end"                           : END,
				self.agent_specific_role.lower(): self.agent_specific_role.lower()
			}
		)
		workflow.add_edge(self.agent_specific_role.lower(), "agent")
		workflow.set_entry_point("agent")
		return workflow.compile().with_config(run_name=f"PAR_Team_Member_Agent_{self.agent_specific_role}")


class ArxivSearchAgentGraph(SearchAgentGraph):
	def __init__(self):
		super().__init__(Custom_arXivSearchTool(), "ArXiv")
		self.search_func = arxiv_search_v2


class BraveSearchAgentGraph(SearchAgentGraph):
	def __init__(self):
		super().__init__(Custom_BraveSearchResults(), "Brave")
		self.search_func = brave_search_func


class TavilySearchAgentGraph(SearchAgentGraph):
	def __init__(self):
		super().__init__(Custom_TavilySearchResults(), "Tavily")
		self.search_func = tavily_search_func


class WikipediaSearchAgentGraph(SearchAgentGraph):
	def __init__(self):
		super().__init__(Custom_WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper()), "Wikipedia")
		self.search_func = wikipedia_search


class YoutubeSearchAgentGraph(SearchAgentGraph):
	def __init__(self):
		super().__init__(Custom_YouTubeSearchTool(), "Youtube")
		self.search_func = youtube_search_v2
