import json
from typing import Optional, Type

from langchain_community.utilities.wikipedia import WikipediaAPIWrapper
from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.tools import BaseTool


class SearchInput(BaseModel):
    """Input for the general search tool."""
    query: str = Field(description="search query to look up")


class ArXivSearchInput(BaseModel):
    """Input for the arXiv tool."""
    query: str = Field(description="The search query to look up using the ArXiv Search API.")
    max_results: int = Field(default=2, ge=1, le=3, description="The maximum number of search results to return. Must be between 2 and 6. Default value is 3")


class Custom_WikipediaQueryRun(BaseTool):
    """Tool that searches the Wikipedia API."""

    name: str = "wikipedia"
    description: str = (
        "A tool for searching Wikipedia articles and getting summarized information. "
        "It finds the top 3 most relevant Wikipedia pages based on the provided search query and returns the title and a summary of the full content for each page. "
        "This is useful when you need to quickly gather general information about a topic from a reliable source. "
        "The input should be a well-formed search query, in addition to the search query, you can also specify the maximum number of results to retrieve, allowing for dynamic control over the amount of information returned."
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
        "A tool for searching YouTube videos and getting summarized information about their content. "
        "It finds relevant videos based on the provided search query, retrieves the transcript (if available) for each video, and uses an LLM to generate a concise summary of the video's content. "
        "This is useful when you need to quickly gather information from video sources without watching them in full. "
        "The input should be a well-formed search query, in addition to the search query, you can also specify the maximum number of results to retrieve, allowing for dynamic control over the amount of information returned."
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
        "A tool for searching scientific papers on arXiv. "
        "It finds relevant papers based on the provided search query, downloads the full text of each paper, and uses an LLM to extract and summarize the key points. "
        "This is useful when you need to gather technical information and insights from scientific literature. "
        "The input should be a well-formed search query, in addition to the search query, you can also specify the maximum number of results to retrieve, allowing for dynamic control over the amount of information returned."
    )

    args_schema: Type[BaseModel] = ArXivSearchInput

    def _search(self) -> str:
        return "test"

    def _run(self, query: str, num_results: int) -> str:
        return "test"