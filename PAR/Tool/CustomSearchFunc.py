import json
import arxiv
from langchain.retrievers import ParentDocumentRetriever
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.tools.wikipedia.tool import WikipediaQueryRun
from langchain_community.utilities.wikipedia import WikipediaAPIWrapper
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.stores import BaseStore

from Tool.Custom_TavilySearchResults import Custom_TavilySearchResults, Custom_TavilySearchAPIWrapper


test_extractor_prompt= ChatPromptTemplate.from_template("""You are a professional context extractor.

Given the following question and context, your task is extract any part of the context *AS IS* that is relevant to answer the question.
If none of the context is relevant return NO_OUTPUT.


<restrictions>
1. *DO NOT* edit the extracted parts of the context.
2. *DO NOT* prefixing any response. Just extracted parts of the context.
</restrictions>

> Question: {question}
> Context:
>>>
{context}
>>>
Extracted relevant parts:""")

# llm = get_cohere_model()
# llm = get_anthropic_model(model_name='sonnet')
# chain = test_extractor_prompt | llm | StrOutputParser()

def web_search(
        query: str,
        datastore: BaseStore,
        retriever: ParentDocumentRetriever
):
    print(query)
    print("---SEARCHING IN WEB(Using TAVILY API)---")
    tavily_search_tool = Custom_TavilySearchResults(
        api_wrapper=Custom_TavilySearchAPIWrapper(),
        include_answer=True,
        include_raw_content=True
    )

    try:
        search_results = tavily_search_tool.invoke({"query": query})
        docs = search_results["results"]
        web_results = f"<overall_summary>{search_results['answer']}</overall_summary>"
        raw_content_summary = ""
        for index, doc in enumerate(docs, start=1):
            web_results += (f"<document index='{index}'>\n"
                            "<document_content>\n"
                            f"{doc['content']}"
                            "</document_content>\n"
                            f"<source>{doc['url']}</source>\n"
                            "</document>\n\n")
            # raw_content_summary += chain.invoke({'question': query, 'context': doc['raw_content']}) + "\n\n"

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