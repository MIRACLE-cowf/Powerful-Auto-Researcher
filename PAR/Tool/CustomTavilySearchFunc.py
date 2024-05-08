import requests

from CustomHelper.Custom_Error_Handler import PAR_ERROR, PAR_SUCCESS
from Tool.CustomSearchFunc_v2 import content_extraction_agent
from Tool.Custom_TavilySearchResults import Custom_TavilySearchResults, Custom_TavilySearchAPIWrapper


def _is_pdf(url: str) -> bool:
	if url.lower().endswith(".pdf"):
		return True

	response = requests.get(url)
	if "application/pdf" in response.headers.get('Content-Type'):
		return True
	else:
		return False


def _build_web_results(search_results: dict) -> str:
	web_results = f"<overall_summary>\n{search_results['answer']}\n</overall_summary>\n\n"

	if isinstance(search_results.get("follow_up_questions", []), list) and len(search_results.get("follow_up_questions", [])) > 0:
		web_results += f"<recommended_follow_up_questions>\n"
		for index, follow_up_question in enumerate(search_results["follow_up_questions"], start=1):
			web_results += f"{index}. {follow_up_question}\n"
		web_results += "</recommended_follow_up_questions>\n"

	if isinstance(search_results.get("images", []), list) and search_results.get("images"):
		print(f"<tavily_has_images>\n{search_results['images']}\n</tavily_has_images>")

	return web_results


def _build_raw_contents(docs: list) -> str:
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


def tavily_search_func(
	query: str,
	max_results: int,
):
	print(f"---SEARCHING IN WEB(Using TAVILY API): {query}---")
	tavily_search_tool = Custom_TavilySearchResults(
		api_wrapper=Custom_TavilySearchAPIWrapper(),
		include_answer=True,
		include_raw_content=True,
		max_results=max_results,
		include_image=True,
		# If you increase max results may be hit rate limit and use more token. So be careful! Note: But It perform more high quality documents.
	)
	tavily_search_tool_with_fallbacks = tavily_search_tool.with_fallbacks([tavily_search_tool] * 8)

	try:
		search_results = tavily_search_tool_with_fallbacks.invoke({"query": query})

		if not isinstance(search_results, dict) and "results" in search_results:
			error_message = str(search_results) if isinstance(search_results, str) else "Unexpected error occurred!"
			print(f"---TAVILY SEARCH ERROR: {error_message}---")
			return PAR_ERROR(error_message)

		docs = search_results["results"]
		web_results = _build_web_results(search_results)
		raw_contents = _build_raw_contents(docs)
		_content_extraction_agent = content_extraction_agent()
		extract_raw_contents_result = _content_extraction_agent.invoke({"search_query": query, "search_result": raw_contents})
		web_results += f"\n\n<raw_content_extract>\n{extract_raw_contents_result}\n</raw_content_extract>\n\n"
		print("---TAVILY SEARCH DONE---")
		return PAR_SUCCESS(web_results)
	except Exception as e:
		print(f"---TAVILY SEARCH ERROR: {e}---")
		return PAR_ERROR(e)
