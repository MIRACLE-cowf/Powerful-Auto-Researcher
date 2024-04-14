import json
import arxiv
from langchain.retrievers import ParentDocumentRetriever
from langchain_community.document_loaders.arxiv import ArxivLoader
from langchain_community.document_loaders.youtube import YoutubeLoader
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.tools.wikipedia.tool import WikipediaQueryRun
from langchain_community.utilities.wikipedia import WikipediaAPIWrapper
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.stores import BaseStore

from CustomHelper.ArxivPaperRelevance_Schema import ArxivPaperRelevance
from CustomHelper.load_model import get_anthropic_model
from Tool.Custom_TavilySearchResults import Custom_TavilySearchResults, Custom_TavilySearchAPIWrapper
from langchain import hub


extractor_prompt= hub.pull("miracle/par_webpage_extractor")
youtube_extractor_prompt=hub.pull("miracle/par_youtube_extractor")
arxiv_extract_prompt=hub.pull("miracle/par_arxiv_extractor")

# llm = get_cohere_model()
llm = get_anthropic_model(model_name='haiku')
llm_sonnet = get_anthropic_model(model_name='sonnet') # For fallback


extract_tavily_chain = extractor_prompt | llm.with_fallbacks([llm_sonnet]) | StrOutputParser()

def web_search(
        query: str,
        datastore: BaseStore,
        retriever: ParentDocumentRetriever
):
    print(f"---SEARCHING IN WEB(Using TAVILY API): {query}---")
    tavily_search_tool = Custom_TavilySearchResults(
        api_wrapper=Custom_TavilySearchAPIWrapper(),
        include_answer=True,
        include_raw_content=True,
        max_results=2, # If you increase max results may be hit rate limit and use more token. So be careful! Note: But It perform more high quality documents.
    )

    try:
        search_results = tavily_search_tool.invoke({"query": query})

        if isinstance(search_results, dict) and "results" in search_results:
            docs = search_results["results"]
            web_results = f"<overall_summary>{search_results['answer']}</overall_summary>"
            chain_batch_input = [{'question': query, 'context': doc['raw_content']} for doc in docs]
            chain_batch_result = extract_tavily_chain.batch(chain_batch_input)

            for index, result in enumerate(chain_batch_result):
                web_results += (f"<document index='{index + 1}'>\n"
                                "<document_content_snippet>\n"
                                f"{docs[index]['content']}"
                                "</document_content_snippet>\n"
                                "<document_summary_raw_content>\n"
                                f"{result}\n"
                                "</document_summary_raw_content>\n"
                                f"<source>{docs[index]['url']}</source>\n"
                                "</document>\n\n")

            print("---TAVILY SEARCH DONE---")
            return web_results
        else:
            error_message = str(search_results) if isinstance(search_results, str) else "Unexpected error occurred!"
            print(f"---TAVILY SEARCH ERROR: {error_message}---")
            return f"Tavily Search Error! Details: {error_message}\nTry Again!"
    except Exception as e:
        print(f"---TAVILY SEARCH ERROR: {e}---")
        return "Tavily Search Error! Try Again!"


youtube_extractor_chain = youtube_extractor_prompt | llm | StrOutputParser()
def youtube_search(
        query: str
) -> str:
    """Youtube search also updated! Now, LLM is extracting information from YouTube Video that have transcript.
    But in this version, I use concurrent parallel. I will refine this code!"""
    from youtube_search import YoutubeSearch
    print("---SEARCHING IN YOUTUBE---")
    results = YoutubeSearch(query, max_results=3).to_json()
    data = json.loads(results)


    def process_video(index, video):
        try:
            loader = YoutubeLoader.from_youtube_url(f"https://www.youtube.com{video['url_suffix']}",
                                                    add_video_info=True)
            load = loader.load()
            if not load or len(load) == 0:
                return None
            else:
                print(f"----REFINE YOUTUBE TRANSCRIPT {index}---")
                transcript_summary = youtube_extractor_chain.invoke(
                    {"question": query, "transcript": load[0].page_content})

                result = (f"<youtube index={index}\n"
                          f"<title>{video['title']}</title>\n"
                          f"<views>{video['views']}</views>\n"
                          f"<publish_time>{video['publish_time']}</publish_time>\n"
                          f"<link>https://www.youtube.com/{video['url_suffix']}</link>\n"
                          f"<content>\n{transcript_summary}\n</content>\n"
                          f"</youtube>")
                print(f"---REFINE YOUTUBE TRANSCRIPT {index} DONE---")
                return result
        except Exception as E:
            print(f"Error occurred while processing video: {video['url_suffix']}")
            print(f"Error message: {str(E)}")
            return None

    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(process_video, index, video) for index, video in enumerate(data["videos"], start=1)]

        final_results = ""
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result is not None:
                final_results += result

    if not final_results:
        return "There is no relevant search results from YouTube"
    else:
        return final_results


arxiv_extract_chain = (arxiv_extract_prompt.partial(restrictions="1. *ALWAYS* use 'ArxivPaperRelevance' tools for your final result.\n2. Take a careful at the schema of the tool, and use the tool. ArxivPaperRelevance input parameter is quite complex, so be careful to use it!")
                       | llm.with_structured_output(ArxivPaperRelevance).with_fallbacks([llm_sonnet.with_structured_output(ArxivPaperRelevance)])
                       )


def arXiv_search(
        query: str,
        original_question: str,
        provided_section: str,
) -> str:
    """arXiv search also updated!
    Now, it is extracting information from arXiv paper pdf by LLM."""
    print("---SEARCHING IN ARXIV---")
    arxiv_results = ""

    try:
        docs = ArxivLoader(query=query, load_max_docs=3).load()
    except Exception as e:
        error_message = str(e)
        print(f"---ARXIV SEARCH ERROR: {error_message}---")
        return f"ArXiv Search Error! Details: {error_message}\nTry Again!"

    arxiv_results += "<arxiv results>\n"
    print(f'---ARXIV DOC IS GRADING AND EXTRACTING: PARALLEL---')
    arxiv_batch_input = [{'original_question': original_question, 'provided_section': provided_section,
                          'arxiv_document_content': doc.page_content} for doc in docs]
    arxiv_batch_result = arxiv_extract_chain.batch(arxiv_batch_input)

    for index, batch in enumerate(arxiv_batch_result, start=0):
        arxiv_results += f"<document index={index + 1}>\n"
        if isinstance(batch, ArxivPaperRelevance):
            print(f'---REFINE ARXIV DOC{index}-TYPE:ARXIVPAPERRELEVANCE DONE---')
            arxiv_results += batch.as_str()
        else:
            print(f"---REFINE ARXIV DOC{index}-TYPE:STRING DONE---")
            arxiv_results += f"{batch}"

    return arxiv_results


#     client = arxiv.Client()
#     search = arxiv.Search(
#         query=query,
#         max_results=5,
#         sort_by=arxiv.SortCriterion.Relevance
#     )
#     results = client.results(search)
#     arxiv_results = ""
#     for index, r in enumerate(results, start=1):
#         arxiv_results += f"""<papers index="{index}">
# <title>{r.title}</title>
# <link>{r.entry_id}</link>
# <published>{r.published}</published>
# </papers>
# """
#     print("---ARXIV SEARCH DONE---")
#     return arxiv_results


def wikipedia_search(query: str) -> str:
    print("---SEARCHING IN WIKIPEDIA---")
    wikipedia = WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper())
    results = wikipedia.run(query)
    print(f"---WIKIPEDIA SEARCH RESULT---\n{results}")

    print("---WIKIPEDIA SEARCH DONE---")
    return results