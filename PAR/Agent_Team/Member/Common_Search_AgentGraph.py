import operator
from typing import TypedDict, Union, Annotated, Dict, Any

from langchain_community.utilities import WikipediaAPIWrapper
from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.runnables import Runnable
from langgraph.graph import END
from langgraph.graph import StateGraph
from langsmith import traceable

from PAR.Agent_Team.create_agent import create_agent
from PAR.CustomHelper.Agent_outcome_checker import agent_outcome_checker
from PAR.CustomHelper.Custom_Error_Handler import PAR_ERROR, PAR_SUCCESS
from PAR.CustomHelper.load_model import get_anthropic_model
from PAR.Single_Chain.EvaluateSearchResultsChain import get_evaluate_search_results
from PAR.Tool.CustomAskNewsTool import Custom_AskNewsResults
from PAR.Tool.CustomBraveSearchFunc import brave_search_func
from PAR.Tool.CustomSearchFunc_v2 import arxiv_search_v2, youtube_search_v2, wikipedia_search, asknews_search
from PAR.Tool.CustomSearchTool import Custom_arXivSearchTool, Custom_WikipediaQueryRun, Custom_YouTubeSearchTool
from PAR.Tool.CustomTavilySearchFunc import tavily_search_func
from PAR.Tool.Custom_BraveSearchResults import Custom_BraveSearchResults
from PAR.Tool.Custom_TavilySearchResults import Custom_TavilySearchResults


class AgentState(TypedDict):
	section_basic_info: str
	search_result: str
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

	@traceable(name="Run Search Agent", run_type="llm")
	async def __run_agent(self, state: AgentState):
		print(f"$$$ {self.agent_specific_role} AGENT RUN $$$")
		input = state["input"]
		section_info = state["section_basic_info"]
		intermediate_steps = state["intermediate_steps"]
		return await agent_outcome_checker(
			agent=self.agent,
			input={
				"input": input,
				"section_info": section_info,
			},
			intermediate_steps=intermediate_steps
		)

	@traceable(name="Run Search Router")
	def __router(self, state: AgentState):
		if isinstance(state["agent_outcome"], AgentFinish):
			return 'end'
		else:
			return self.agent_specific_role.lower()

	@traceable(name="Run Search Tool", run_type="tool")
	async def __search_node(self, state: AgentState):
		print(f"$$$ {self.agent_specific_role} AGENT PERFORM SEARCH $$$")
		agent_action = state['agent_outcome']
		max_results = agent_action.tool_input.get('max_results', None)

		# print(f"search node's agent action: {agent_action}")
		try:
			search_result = await self.search_func(
				query=agent_action.tool_input['query'],  # 여기서 자꾸 KeyError 'query' 발생함
				max_results=max_results
			)
			return {
				'search_result': search_result,
			}

		except Exception as e:
			# print(f"search node's agent action: {agent_action}")
			print(f"search node's search error detail: {str(e)}")
			raise PAR_ERROR(str(e))

	@traceable(name="Run Feedback Node", run_type="llm")
	async def __feedback_node(self, state: AgentState):
		print(f"$$$ {self.agent_specific_role} AGENT PERFORM FEEDBACK $$$")
		agent_action = state['agent_outcome']
		_search_result = state["search_result"]
		_pm_instructions = state["input"]
		_section_info = state["section_basic_info"]
		if isinstance(_search_result, PAR_SUCCESS):
			search_result = _search_result.result
			feedback_result = await get_evaluate_search_results(
				web_results=search_result,
				pm_instructions=_pm_instructions,
				section_info=_section_info
			)
			result = search_result + "<feedback>\n" + feedback_result + "</feedback>"
			return {
				'intermediate_steps': [(agent_action, PAR_SUCCESS(result))]
			}
		elif isinstance(_search_result, PAR_ERROR):
			return {
				'intermediate_steps': [(agent_action, _search_result)]
			}
		else:
			print(f"Type of '_search_result' is {type(_search_result)}")
			raise TypeError(type(_search_result))
			# return {
			# 	'intermediate_steps': [(agent_action, _search_result)]
			# }

	def get_search_agent_graph(self) -> Runnable:
		workflow = StateGraph(AgentState)
		workflow.add_node("search_agent", self.__run_agent)
		workflow.add_node(self.agent_specific_role.lower(), self.__search_node)
		workflow.add_node("feedback_agent", self.__feedback_node)

		workflow.add_conditional_edges(
			"search_agent",
			self.__router,
			{
				"end"                           : END,
				self.agent_specific_role.lower(): self.agent_specific_role.lower()
			}
		)
		workflow.add_edge(self.agent_specific_role.lower(), "feedback_agent")
		workflow.add_edge("feedback_agent", "search_agent")
		workflow.set_entry_point("search_agent")
		return workflow.compile()

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


class AskNewsSearchAgentGraph(SearchAgentGraph):
	def __init__(self):
		super().__init__(Custom_AskNewsResults(), agent_specific_role="AskNews")
		self.search_func = asknews_search
