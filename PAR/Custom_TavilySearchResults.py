from typing import Optional, Union, List, Dict

from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.utilities.tavily_search import TavilySearchAPIWrapper
from langchain_core.callbacks import CallbackManagerForToolRun, AsyncCallbackManagerForToolRun


class Custom_TavilySearchResults(TavilySearchResults):
    include_answer = False
    include_raw_content = False


    def _run(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Union[List[Dict], str]:
        """Use the tool."""
        try:
            return self.api_wrapper.results(
                query=query,
                max_results=self.max_results,
                include_answer=self.include_answer,
                include_raw_content=self.include_raw_content
            )
        except Exception as e:
            return repr(e)

    async def _arun(
        self,
        query: str,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> Union[List[Dict], str]:
        """Use the tool asynchronously."""
        try:
            return await self.api_wrapper.results_async(
                query=query,
                max_results=self.max_results,
                include_answer=self.include_answer,
                include_raw_content=self.include_raw_content
            )
        except Exception as e:
            return repr(e)


class Custom_TavilySearchAPIWrapper(TavilySearchAPIWrapper):

    def results(
            self,
            query: str,
            max_results: Optional[int] = 5,
            search_depth: Optional[str] = "advanced",
            include_domains: Optional[List[str]] = [],
            exclude_domains: Optional[List[str]] = [],
            include_answer: Optional[bool] = False,
            include_raw_content: Optional[bool] = False,
            include_images: Optional[bool] = False,
    ) -> Dict:
        """Run query through Tavily Search and return metadata.

        Args:
            query: The query to search for.
            max_results: The maximum number of results to return.
            search_depth: The depth of the search. Can be "basic" or "advanced".
            include_domains: A list of domains to include in the search.
            exclude_domains: A list of domains to exclude from the search.
            include_answer: Whether to include the answer in the results.
            include_raw_content: Whether to include the raw content in the results.
            include_images: Whether to include images in the results.
        Returns:
            query: The query that was searched for.
            follow_up_questions: A list of follow up questions.
            response_time: The response time of the query.
            answer: The answer to the query.
            images: A list of images.
            results: A list of dictionaries containing the results:
                title: The title of the result.
                url: The url of the result.
                content: The content of the result.
                score: The score of the result.
                raw_content: The raw content of the result.
        """  # noqa: E501
        raw_search_results = self.raw_results(
            query,
            max_results=max_results,
            search_depth=search_depth,
            include_domains=include_domains,
            exclude_domains=exclude_domains,
            include_answer=include_answer,
            include_raw_content=include_raw_content,
            include_images=include_images,
        )
        if include_answer:
            return self.clean_results(raw_search_results["results"], raw_search_results["answer"])
        else:
            return self.clean_results(raw_search_results["results"])

    def clean_results(self, results: List[Dict], answer: str = None) -> Dict:
        final_results = {}
        clean_results = []
        if answer is not None:
            final_results["answer"] = answer
        for result in results:
            clean_result = {
                "url": result["url"],
                "content": result["content"]
            }
            if "raw_content" in result:
                clean_result["raw_content"] = result["raw_content"]
            clean_results.append(clean_result)
        final_results["results"] = clean_results
        return final_results