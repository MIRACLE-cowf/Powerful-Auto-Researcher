import json
from typing import Optional, Type

from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import BaseTool
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_community.utilities.wikipedia import WikipediaAPIWrapper


class SearchInput(BaseModel):
    """Input for the Tavily tool."""

    query: str = Field(description="search query to look up")


class Custom_WikipediaQueryRun(BaseTool):
    """Tool that searches the Wikipedia API."""

    name: str = "wikipedia"
    description: str = (
        "A wrapper around Wikipedia. "
        "Useful for when you need to answer general questions about "
        "people, places, companies, facts, historical events, or other subjects. "
        "Input should be a search query."
    )
    api_wrapper: WikipediaAPIWrapper
    args_schema: Type[BaseModel] = SearchInput

    def _run(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Use the Wikipedia tool."""
        return self.api_wrapper.run(query)


class Custom_YouTubeSearchTool(BaseTool):
    """Tool that queries YouTube."""

    name: str = "youtube_search"
    description: str = (
        "search for youtube videos associated with a query."
        "Input should be a search query."
    )

    args_schema: Type[BaseModel] = SearchInput

    def _search(self, person: str, num_results: int) -> str:
        from youtube_search import YoutubeSearch

        results = YoutubeSearch(person, num_results).to_json()
        data = json.loads(results)
        url_suffix_list = [
            "https://www.youtube.com" + video["url_suffix"] for video in data["videos"]
        ]
        return str(url_suffix_list)

    def _run(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Use the tool."""
        values = query.split(",")
        person = values[0]
        if len(values) > 1:
            num_results = int(values[1])
        else:
            num_results = 2
        return self._search(person, num_results)


class Custom_arXivSearchTool(BaseTool):
    name: str = "arXiv_search"
    description: str = (
        "search for arXiv papers associated with a query."
        "Input should be a search query."
    )

    args_schema: Type[BaseModel] = SearchInput

    def _search(self) -> str:
        return "test"

    def _run(self, query: str, num_results: int) -> str:
        return "test"