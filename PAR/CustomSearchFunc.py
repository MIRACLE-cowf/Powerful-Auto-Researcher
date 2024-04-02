import json
from arxiv import arxiv
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.tools.wikipedia.tool import WikipediaQueryRun
from langchain_community.utilities.wikipedia import WikipediaAPIWrapper


def web_search(
        query: str
):
    print(query)
    print("---SEARCHING IN WEB(Using TAVILY API)---")
    tool = TavilySearchResults()

    try:
        docs = tool.invoke({"query": query, "include_answer": True})
        web_results = ""
        for index, doc in enumerate(docs, start=1):
            web_results += f"""<document index="{index}">
<document_content>
{doc["content"]}
</document_content>
<source>{doc['url']}</source>
</document>
"""

        print("---TAVILY SEARCH DONE---")
        return web_results
    except Exception as e:
        print(f"---TAVILY SEARCH ERROR: {e}---")
        return "Tavily Search Error! Try Again!"


def youtube_search(
        query: str
) -> str:
    from youtube_search import YoutubeSearch
    print("---SEARCHING IN YOUTUBE---")
    results = YoutubeSearch(query, max_results=5).to_json()
    data = json.loads(results)

    final_results = ""
    for index, video in enumerate(data["videos"], start=1):
        final_results += f"""<youtube index="{index}">
<title>{video['title']}</title>
<views>{video['views']}</views>
<publish_time>{video['publish_time']}</publish_time>
<link>https://www.youtube.com{video['url_suffix']}</link>
</youtube>
"""
    print("---YOUTUBE SEARCH DONE---")
    return final_results


def arXiv_search(
        query: str
) -> str:
    print("---SEARCHING IN ARXIV---")
    client = arxiv.Client()
    search = arxiv.Search(
        query=query,
        max_results=5,
        sort_by=arxiv.SortCriterion.Relevance
    )
    results = client.results(search)
    arxiv_results = ""
    for index, r in enumerate(results, start=1):
        arxiv_results += f"""<papers index="{index}">
<title>{r.title}</title>
<link>{r.entry_id}</link>
<published>{r.published}</published>
</papers>
"""
    print("---ARXIV SEARCH DONE---")
    return arxiv_results


def wikipedia_search(query: str) -> str:
    print("---SEARCHING IN WIKIPEDIA---")
    wikipedia = WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper())
    results = wikipedia.run(query)
    print(f"---WIKIPEDIA SEARCH RESULT---\n{results}")

    print("---WIKIPEDIA SEARCH DONE---")
    return results