import operator
from typing import TypedDict, Union, Annotated, Dict, Any

from langchain_community.utilities import WikipediaAPIWrapper
from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.runnables import Runnable
from langgraph.graph import END
from langgraph.graph import StateGraph

from Agent_Team.create_agent import create_agent
from CustomHelper.Agent_outcome_checker import agent_outcome_checker
from CustomHelper.Custom_Error_Handler import PAR_ERROR
from CustomHelper.load_model import get_anthropic_model
from Tool.CustomBraveSearchFunc import brave_search_func
from Tool.CustomSearchFunc import wikipedia_search
from Tool.CustomSearchFunc_v2 import arxiv_search_v2, youtube_search_v2
from Tool.CustomSearchTool import Custom_arXivSearchTool, Custom_WikipediaQueryRun, Custom_YouTubeSearchTool
from Tool.CustomTavilySearchFunc import tavily_search_func
from Tool.Custom_BraveSearchResults import Custom_BraveSearchResults
from Tool.Custom_TavilySearchResults import Custom_TavilySearchResults


class AgentState(TypedDict):
	section_basic_info: str
	agent_outcome: Union[AgentAction, AgentFinish, None]
	intermediate_steps: Annotated[list[tuple[AgentAction, str]], operator.add]
	keys: Dict[str, Any]
	input: str


class SearchAgentGraph:
	def __init__(self, tool, agent_specific_role):
		self.search_func = None
		self.tool = tool
		self.agent_specific_role = agent_specific_role
		self.agent = create_agent(llm=get_anthropic_model(model_name="sonnet"), tool=tool, agent_specific_role=agent_specific_role)

	async def __run_agent(self, data: AgentState):
		input = data["input"]
		section_info = data["section_basic_info"]
		intermediate_steps = data["intermediate_steps"]
		return await agent_outcome_checker(
			agent=self.agent,
			input={
				"input": input,
				"section_info": section_info,
			},
			intermediate_steps=intermediate_steps
		)

	def __router(self, data: AgentState):
		if isinstance(data["agent_outcome"], AgentFinish):
			return 'end'
		else:
			return self.agent_specific_role.lower()

	async def __search_node(self, data: AgentState):
		agent_action = data['agent_outcome']
		max_results = agent_action.tool_input.get('max_results', None)

		print(f"search node's agent action: {agent_action}")
		try:
			search_result = await self.search_func(
				query=agent_action.tool_input['query'],  # 여기서 자꾸 KeyError 'query' 발생함
				max_results=max_results
			)
			return {
				'intermediate_steps': [(agent_action, search_result)]
			}
		except Exception as e:
			print(f"search node's agent action: {agent_action}")
			print(f"search node's search error detail: {str(e)}")
			raise PAR_ERROR(str(e))

	def get_search_agent_graph(self) -> Runnable:
		workflow = StateGraph(AgentState)
		workflow.add_node("search_agent", self.__run_agent)
		workflow.add_node(self.agent_specific_role.lower(), self.__search_node)

		workflow.add_conditional_edges(
			"search_agent",
			self.__router,
			{
				"end"                           : END,
				self.agent_specific_role.lower(): self.agent_specific_role.lower()
			}
		)
		workflow.add_edge(self.agent_specific_role.lower(), "search_agent")
		workflow.set_entry_point("search_agent")
		return workflow.compile().with_config(run_name=f"{self.agent_specific_role} Search Agent")

	def get_search_agent_graph_mermaid(self):
		print("Search Agent Graph Mermaid")
		print(self.get_search_agent_graph().get_graph().draw_mermaid())


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

