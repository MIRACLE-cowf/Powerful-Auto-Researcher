from pprint import pprint

from dotenv import load_dotenv

from Custom.Custom_BraveSearchResults import get_brave_search_tool, build_search_results_item_brave
from Custom.Custom_TavilySearchResults import get_tavily_search_tool, build_search_results_item_tavily

load_dotenv()


def run_tavily_search(query: str) -> list[dict]:
	print(f"run tavily search: query: {query}")
	tavily_tool = get_tavily_search_tool(max_results=5)
	search_results = tavily_tool.invoke({'query': query})
	print(search_results)
	results = build_search_results_item_tavily(search_results['results'])
	return results
	# from pprint import pprint
	# pprint(results)


def run_brave_search(query: str) -> list[dict]:
	brave_tool = get_brave_search_tool(max_results=5)
	search_results = brave_tool.invoke({'query': query})
	results = build_search_results_item_brave(search_results)
	return results


if __name__ == '__main__':
	pprint(run_tavily_search('Compose multiplatform'))