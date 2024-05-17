from typing import Optional, Union

import requests

from CustomHelper.Custom_Error_Handler import PAR_ERROR, PAR_SUCCESS
from CustomHelper.Helper import retry_with_delay_async
from Tool.CustomSearchFunc_v2 import _get_content_extraction_agent
from Tool.Custom_TavilySearchResults import Custom_TavilySearchResults, Custom_TavilySearchAPIWrapper


def _is_pdf(url: str) -> bool:
	if not url:
		return False
	if url.lower().endswith(".pdf"):
		return True

	try:
		response = requests.get(url)
		response.raise_for_status()
		return 'application/pdf' in response.headers.get('Content-Type', '')
	except Exception as e:
		return False


def _build_tavily_results(search_results: dict) -> str:
	web_results = ""
	if isinstance(search_results.get("answer", ""), str):
		web_results = f"<overall_summary>\n{search_results['answer']}\n</overall_summary>\n\n"

	if isinstance(search_results.get("follow_up_questions", []), list) and len(search_results.get("follow_up_questions", [])) > 0:
		web_results += f"<recommended_follow_up_questions>\n"
		for index, follow_up_question in enumerate(search_results["follow_up_questions"], start=1):
			web_results += f"{index}. {follow_up_question}\n"
		web_results += "</recommended_follow_up_questions>\n"

	# if isinstance(search_results.get("images", []), list) and search_results.get("images"):
	# 	print(f"<tavily_has_images>\n{search_results['images']}\n</tavily_has_images>")

	return web_results


def _build_raw_contents(docs: list) -> str:
	if docs is None:
		return ""  # docs가 None인 경우 빈 문자열 반환

	raw_contents = ""
	for index, doc in enumerate(docs, start=1):

		if _is_pdf(doc['url']):
			continue

		raw_contents += (f"<document index='{index}'>\n"
		                 "<document_content_snippet>\n"
		                 f"{doc['content']}"
		                 "</document_content_snippet>\n"
		                 "<document_raw_content>\n"
		                 f"{doc['raw_content']}\n"
		                 "</document_raw_content>\n"
		                 f"<source>{doc['url']}</source>\n"
		                 "</document>\n\n")

	return raw_contents


async def tavily_search_func(
	query: str,
	max_results: Optional[int] = None,
) -> Union[PAR_SUCCESS, PAR_ERROR]:
	if max_results is None:
		max_results = 5

	print(f"---SEARCHING IN WEB(Using TAVILY API): {query}---")
	tavily_search_tool = Custom_TavilySearchResults(
		api_wrapper=Custom_TavilySearchAPIWrapper(),
		include_answer=True,
		include_raw_content=True,
		max_results=max_results,
		include_image=True,
		# If you increase max results may be hit rate limit and use more token. So be careful! Note: But It perform more high quality documents.
	)
	tavily_search_tool_with_fallbacks = tavily_search_tool.with_fallbacks([tavily_search_tool] * 60)

	try:
		search_results = await tavily_search_tool_with_fallbacks.ainvoke({"query": query + "."})

		if not isinstance(search_results, dict) and "results" in search_results:
			error_message = str(search_results) if isinstance(search_results, str) else "Unexpected error occurred!"
			print(f"---TAVILY SEARCH ERROR: standard: {error_message}---")
			return PAR_ERROR(error_message)

		docs = search_results["results"]
		web_results = _build_tavily_results(search_results)
		raw_contents = _build_raw_contents(docs)
		_content_extraction_agent = _get_content_extraction_agent()
		extract_raw_contents_result = await retry_with_delay_async(
			chain=_content_extraction_agent,
			input={
				"search_query": query,
				"search_result": raw_contents,
			},
			max_retries=5,
			delay_seconds=45.0
		)
		# extract_raw_contents_result = await _content_extraction_agent.ainvoke({"search_query": query, "search_result": raw_contents})
		web_results += f"\n\n<raw_content_extract>\n{extract_raw_contents_result}\n</raw_content_extract>\n\n"
		print("---TAVILY SEARCH DONE---")
		return PAR_SUCCESS(web_results)
	except Exception as e:
		print(f"---TAVILY SEARCH ERROR: {e}---")
		return PAR_ERROR(str(e))


if __name__ == "__main__":
	result = tavily_search_func(
		query="importance of short-term price forecasting for agricultural commodities.",
		max_results=3
	)
	print(result.result)