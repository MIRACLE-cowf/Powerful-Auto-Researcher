import asyncio
from typing import Optional, Union

from langsmith import traceable

from CustomHelper.Custom_Error_Handler import PAR_SUCCESS, PAR_ERROR
from CustomHelper.Helper import retry_with_delay_async
from Tool.CustomSearchFunc_v2 import _get_content_extraction_agent
from Tool.Custom_BraveSearchResults import get_brave_search_tool


def _build_brave_results(search_results: dict) -> str:
	web_results = ""
	_brave_results = search_results['brave_search']['web']['results']
	_summary_results = search_results.get('summary_search', None)

	for index, _result in enumerate(_brave_results, start=1):
		web_results += (f"<document index='{index}'>\n"
		                f"<title>{_result['title']}</title>\n"
		                f"<source>{_result['url']}</source>\n"
		                f"<description>\n{_result['description']}\n</description>\n")

		if _result.get('extra_snippets', None) is not None:
			web_results += f"<extra_snippets>\n"
			for index, snippet in enumerate(_result['extra_snippets'], start=1):
				web_results += (f"<snippet index={index}>\n"
				                f"{snippet}\n"
				                f"</snippet>\n")
			web_results += ("</extra_snippets>\n")

	if _summary_results is not None:
		web_results += f"<ai_summarize>\n{_summary_results}</ai_summarize>\n"

	return web_results


@traceable(name="Brave Search", run_type="tool")
async def brave_search_func(
	query: str,
	max_results: Optional[int] = None,
) -> Union[PAR_SUCCESS, PAR_ERROR]:
	print(f"---SEARCHING IN WEB(Using Brave Search API): {query}---")

	brave_search_tool_with_fallbacks = get_brave_search_tool(max_results=max_results)

	try:
		search_results = await brave_search_tool_with_fallbacks.ainvoke({'query': query + "."})

		web_results = _build_brave_results(search_results)
		_content_extraction_agent = _get_content_extraction_agent()
		extract_raw_contents_results = await retry_with_delay_async(
			chain=_content_extraction_agent,
			input={
				"search_query": query,
				"search_result": web_results
			},
			max_retries=5,
			delay_seconds=45.0,
		)

		return PAR_SUCCESS(extract_raw_contents_results)
	except Exception as e:
		print(f'---BRAVE SEARCH ERROR: {e}---')
		return PAR_ERROR(str(e))


if __name__ == '__main__':
	result = asyncio.run(brave_search_func(
		query="GDP rankings by country",
		max_results=5,
	))
	print(result.result)
