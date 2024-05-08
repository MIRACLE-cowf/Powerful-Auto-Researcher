from typing import Union

from langchain_community.document_loaders.arxiv import ArxivLoader
from langchain_community.document_loaders.youtube import YoutubeLoader
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableSerializable

from CustomHelper.Custom_Error_Handler import PAR_SUCCESS, PAR_ERROR
from CustomHelper.Helper import retry_with_delay
from CustomHelper.load_model import get_anthropic_model


def content_extraction_agent() -> RunnableSerializable:
    content_extraction_prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an information extraction specialized agent with extensive experience in collecting data from raw content.

    Currently, you are a team member of the PAR project, working on writing a specific section of an entire markdown document. Other search engine agents have collected and delivered content to you.

    Your role is to extract key information that will help in writing the section when given the raw content and search queries used by the search engine agents.

    <instructions>
    1. Analyze the given search queries to identify the core keywords and intent.
    - Identify the main concepts, entities, actions, etc., included in the search queries.
    - Understand the context and purpose of the search queries.
    2. Analyze and process each raw content individually.
    - Treat each raw content separated by XML tags as an independent unit of information.
    - Remove unnecessary elements and focus on the textual information.
    - Analyze the information at the paragraph and sentence level and evaluate its relevance to the search queries.
    3. Prioritize extracting key information directly related to the search queries.
    - Identify paragraphs or sentences that align with the keywords and intent of the search queries.
    - Determine if the extracted information will be helpful in writing the section.
    - Preserve the original text of the extracted information as much as possible, but include the surrounding context when necessary to clarify the meaning.
    4. Clearly indicate the source of the extracted information.
    - Provide the original URL for each piece of extracted information.
    - Ensure that it is identifiable which raw content the extracted information comes from.
    5. Provide a summary along with the extracted information.
    - Clearly convey the extracted key information.
    - Present the relationships or differences between the extracted pieces of information.
    - Additionally, provide a summary alongside the extracted information.
    - Offer the summarized information in a form that can be directly utilized in writing the section.
    </instructions>


    <restrictions>
    1. Always consider the relevance to the search queries.
    - The extracted information should align with the context and purpose of the search queries.
    - Exclude information that is unrelated to the search queries from the extraction process.
    2. Prioritize the accuracy and reliability of the information.
    - The extracted information should be based on the original text and adhere to factual relationships.
    - Exclude information from unclear or unreliable sources.
    - Avoid speculation or subjective interpretation and rely on objective facts based on the original text.
    3. Comply with copyright and licensing requirements.
    - Specify the source of the extracted information and respect copyright.
    4. Avoid unnecessary repetition or duplicate work and focus on extracting key information.
    </restrictions>


    <response_format>
    When delivering the extracted information, please use the following format:

    Extracted Information 1:
    Source: [Title or description of the source]
    URL: [URL of the original content]
    Content: [Extracted information preserving the original text]

    Extracted Information 2:
    Source: [Title or description of the source]
    URL: [URL of the original content]
    Content: [Extracted information preserving the original text]

    ...

    Summary:
    [Concise summary of the extracted information]

    [Insights and analysis of the relationships or differences among the extracted information]
    </response_format>

    As an information extraction specialized agent, extract the most relevant and reliable information from the provided raw content based on the given search queries. Follow the guidelines and restrictions mentioned above to contribute effectively to the PAR project."""),
        ("human", "<search_query>\n{search_query}\n</search_query>\n"
                  "<search_results>\n{search_result}\n</search_results>")
    ])
    content_extraction_llm = get_anthropic_model()
    content_extraction_chain = (
            {
                "search_query" : lambda x: x["search_query"],
                "search_result": lambda x: x["search_result"]
            }
            | content_extraction_prompt
            | retry_with_delay(llm=content_extraction_llm, max_retries=10, delay_seconds=60.0)
            | StrOutputParser()
    )
    return content_extraction_chain


def transform_raw_content(index: int, raw_content: str) -> str:
    return f"<raw_content_{index}>\n{raw_content}\n</raw_content_{index}>\n\n"


# def web_search_v2(
#     query: str,
#     max_results: int
# ) -> Union[PAR_SUCCESS, PAR_ERROR]:
#     print(f"---SEARCHING IN WEB(Using TAVILY API): {query}---")
#     tavily_search_tool = Custom_TavilySearchResults(
#         api_wrapper=Custom_TavilySearchAPIWrapper(),
#         include_answer=True,
#         include_raw_content=True,
#         max_results=max_results,
#         include_image=True,
#         # If you increase max results may be hit rate limit and use more token. So be careful! Note: But It perform more high quality documents.
#     )
#
#     tavily_search_tool_with_fallbacks = tavily_search_tool.with_fallbacks([tavily_search_tool] * 20)
#
#     try:
#         search_results = tavily_search_tool_with_fallbacks.invoke({"query": query})
#
#         if isinstance(search_results, dict) and "results" in search_results:
#             docs = search_results["results"]
#             web_results = f"<overall_summary>\n{search_results['answer']}\n</overall_summary>\n\n"
#             if isinstance(search_results.get("follow_up_questions", []), list) and len(search_results.get("follow_up_questions", [])) > 0:
#                 web_results += f"<recommended_follow_up_questions>\n"
#                 for index, follow_up_question in enumerate(search_results.get("follow_up_questions"), start=1):
#                     web_results += f"{index}. {follow_up_question}\n"
#                 web_results += "</recommended_follow_up_questions>\n"
#             else:
#                 pass
#
#             if isinstance(search_results.get("images", []), list) and len(search_results.get("images", [])) > 0:
#                 print(f"<tavily_has_images>\n{search_results.get('images')}\n</tavily_has_images>")
#
#             raw_contents = f"<overall_summary>\n{search_results['answer']}\n</overall_summary>\n\n"
#             for index, doc in enumerate(docs, start=1):
#                 if doc['url'].lower().endswith(".pdf"):
#                     # we don't need to pdf.
#                     continue
#                 raw_contents += (f"<document index='{index}'>\n"
#                                  "<document_content_snippet>\n"
#                                  f"{doc['content']}"
#                                  "</document_content_snippet>\n"
#                                  "<document_raw_content>\n"
#                                  f"{doc['raw_content']}\n"
#                                  "</document_raw_content>\n"
#                                  f"<source>{doc['url']}</source>\n"
#                                  "</document>\n\n")
#
#             extract_raw_contents_result = content_extraction_agent.invoke({"search_query": query, "search_result": raw_contents})
#             web_results += f"\n\n<raw_content_extract>\n{extract_raw_contents_result}\n</raw_content_extract>\n\n"
#             print("---TAVILY SEARCH DONE---")
#             return PAR_SUCCESS(web_results)
#             # return web_results
#         else:
#             error_message = str(search_results) if isinstance(search_results, str) else "Unexpected error occurred!"
#             print(f"---TAVILY SEARCH ERROR: {error_message}---")
#             return PAR_ERROR(error_message)
#             # return f"Tavily Search Error! Details: {error_message}\nTry Again!"
#     except Exception as e:
#         print(f"---TAVILY SEARCH ERROR: {e}---")
#         return PAR_ERROR(str(e))
#         # return "Tavily Search Error! Try Again!"


def youtube_search_v2(
        query: str
) -> Union[PAR_SUCCESS, PAR_ERROR]:
    from youtube_search import YoutubeSearch
    print("---SEARCHING IN YOUTUBE---")

    try:
        results = YoutubeSearch(query, max_results=5).to_json()
    except Exception as e:
        return PAR_ERROR(str(e))

    import json
    data = json.loads(results)
    youtube_results = ""

    for index, video in enumerate(data["videos"], start=1):
        loader = YoutubeLoader.from_youtube_url(f"https://www.youtube.com{video['url_suffix']}",
                                                add_video_info=True)
        try:
            load = loader.load()

            if not load and len(load) == 0:
                continue
            else:
                youtube_results += (f"<youtube index={index}\n"
                                    f"<title>{video['title']}</title>"
                                    f"<views>{video['views']}</views>"
                                    f"<publish_time>{video['publish_time']}</publish_time>"
                                    f"<link>https://www.youtube.com/{video['url_suffix']}</link>"
                                    f"<content>{load[0].page_content}</content>"
                                    f"</youtube>\n\n")
        except Exception as e:
            print(f"Error occurred while loading video: {str(e)}")
            pass
    _content_extraction_agent = content_extraction_agent()
    youtube_extract_results = _content_extraction_agent.invoke({"search_query": query, "search_result": youtube_results})
    return PAR_SUCCESS(youtube_extract_results)


def arxiv_search_v2(
    query: str,
    max_results: int
) -> Union[PAR_SUCCESS, PAR_ERROR]:
    arxiv_results = ""
    try:
        docs = ArxivLoader(query=query, load_max_docs=max_results, load_all_available_meta=True).load()
    except Exception as e:
        error_message = str(e)
        print(f"---ARXIV SEARCH ERROR: {error_message}---")
        return PAR_ERROR(error_message)

    arxiv_results += "<arxiv results>\n"
    print(f'---ARXIV DOC IS GRADING AND EXTRACTING: PARALLEL---')

    def convert_arxiv_raw_data_to_raw_content(doc) -> str:
        return (f"<arxiv paper title>{doc.metadata['Title']}</arxiv paper>\n"
                f"<arxiv paper published>{doc.metadata['Published']}</arxiv paper>\n"
                f"<arxiv entry_id>{doc.metadata['entry_id']}</arxiv entry_id>\n"
                f"<arxiv paper raw content>\n{doc.page_content}\n</arxiv paper raw content>")

    arxiv_batch_input = [{'search_query': query, 'search_result': convert_arxiv_raw_data_to_raw_content(doc)} for doc in
                         docs]
    _content_extraction_agent = content_extraction_agent()
    arxiv_batch_result = _content_extraction_agent.batch(arxiv_batch_input)

    for index, batch in enumerate(arxiv_batch_result, start=1):
        arxiv_results += (f"<document index={index}>\n"
                          f"<extract_result>\n{batch}</extract_result>\n</document>\n\n")

    return PAR_SUCCESS(arxiv_results)
