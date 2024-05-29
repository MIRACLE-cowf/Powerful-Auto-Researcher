from typing import Type, Optional, Union, List, Dict

from langchain_community.retrievers import AskNewsRetriever
from langchain_core.callbacks import CallbackManagerForToolRun, AsyncCallbackManagerForToolRun
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.tools import BaseTool


class AskNewsInput(BaseModel):
	"""Input for the AskNews tool."""

	query: str = Field(description="The search query to look up using the AskNews Search")
	max_results: int = Field(default=3, ge=2, le=6, description="The maximum number of search results to return. Must be between 2 and 6. Default value is 3")


class Custom_AskNewsResults(BaseTool):
	name: str = "asknews_search_results"
	description: str = (
		"Use AskNews when you need the most up-to-date information on current events, breaking news, and trending stories from around the world. "
		"AskNews leverages advanced AI techniques to process and index over 300,000 news articles per day from 50,000 diverse sources across 100+ countries and 13 languages."
	)
	max_results: int = 5
	args_schema: Type[BaseModel] = AskNewsInput

	def _run(
		self,
		query: str,
		run_manager: Optional[CallbackManagerForToolRun] = None,
	) -> Union[List[Dict], str]:
		try:
			retriever = AskNewsRetriever(k=self.max_results)
			docs = retriever.invoke(query)
			pretty_str = ""
			for doc in docs:
				pretty_str += doc.page_content
			return pretty_str
		except Exception as e:
			return repr(e)

	async def _arun(
		self,
		query: str,
		run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
	) -> Union[List[Dict], str]:
		try:
			retriever = AskNewsRetriever(k=self.max_results)
			docs = await retriever.ainvoke(query)
			pretty_str = ""
			for doc in docs:
				pretty_str += doc.page_content
			return pretty_str
		except Exception as e:
			return repr(e)
