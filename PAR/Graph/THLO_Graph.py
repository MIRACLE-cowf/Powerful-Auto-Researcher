from operator import itemgetter
from typing import TypedDict

from langchain import hub
from langgraph.graph import StateGraph

from CustomHelper.THLO_helper import Thought, HighLevelDocument_Outline, HighLevelDocument_Plan
from CustomHelper.load_model import get_openai_model

thought_prompt = hub.pull("miracle/par_thought_prompt_public")
high_level_outline_prompt = hub.pull("miracle/par_high_level_outline_prompt_public")
generate_search_query_plans_prompt = hub.pull("miracle/par_generate_search_query_prompt_public")


# This THLO stage is very important and powerful stage in PAR architecture, so we try to use high-quality model.
# Note: But it can also pretty good with "haiku" and "sonnet"
# Just your judgement. But I'm use "opus" at "high level outline" stage.

# thought_llm = get_anthropic_model(model_name="sonnet")
# high_level_outline_llm = get_anthropic_model(model_name="opus")
# generate_search_query_plans_llm = get_anthropic_model(model_name="opus")
# generate_search_query_plans_fallback_final = get_anthropic_model(model_name="opus")

thought_llm = get_openai_model(model_name="gpt4")
high_level_outline_llm = get_openai_model(model_name="gpt4")
generate_search_query_plans_llm = get_openai_model(model_name="gpt4")
generate_search_query_plans_fallback_final = get_openai_model(model_name="gpt4")


def thought_output_parser(thought: Thought) -> dict:
    return {
        "inner_monologue": thought
    }


def high_level_outline_parser(outline: HighLevelDocument_Outline) -> dict:
    return {
        "high_level_outline": outline
    }


def generate_search_query_plans_parser(plan: HighLevelDocument_Plan) -> dict:
    return {
        "search_query_engine_plan": plan
    }


thought_chain = thought_prompt | thought_llm.with_structured_output(Thought) | thought_output_parser

search_engines_description = """Search Engine 1:
>> name: Tavily
>> description: Use this tool when you need reliable searches on a wide range of topics. It performs deep searches focusing on materials from trustworthy sites and is suitable for most general searches. Tavily excels in searching for topics with low volatility or when detailed content is required. It is useful for academic research, in-depth information on specific domains, historical facts, or areas with low variability, as well as when collecting quotes or data from reliable sources. The searches are highly relevant to the query or keywords, resulting in targeted and specialized results. However, the scope of the provided information may be limited to directly related content.
Search Engine 2:
>> name: Wikipedia
>> description: It is an online encyclopedia covering a wide range of topics. It allows you to quickly collect basic information on concepts, people, events, places, etc. from various fields. As it is an online encyclopedia, it is written and edited by many people online. Although efforts are made to maintain the latest information and neutrality of the content, verification with other reliable searches is required. It is suitable for quickly grasping an overview of a topic or domain, confirming the definition of a term, or as a starting point for in-depth research. It contains a lot of information that helps build general common sense and knowledge rather than academic research. However, there may be cases where there are no results when searching for a specific domain or topic. The return results basically provide a pair of the Wikipedia page name for a specific topic and an overall summary of the page content.
Search Engine 3:
>> name: arxiv
>> description: ArXiv is a search engine that shares the latest research in various and wide-ranging scientific fields such as physics, mathematics, computer science, and biology. It is primarily used when highly deep and specialized knowledge, in-depth information, or the latest research techniques and methodologies are needed for a particular topic or domain. It is recommended to selectively utilize arXiv searches only when very professional and technical content is required. The return results basically provide a summary and extraction of specific content by the LLM for the full text of the papers found through the arXiv search.
Search Engine 4:
>> name: youtube
>> description: It is generally optimized for video searches. However, it is not a typical video search but an API-style search. For videos that support transcripts, the LLM looks at the transcript and extracts content directly related to the search query. The return results include the video title, view count, upload date, content extracted by the LLM about the video, and a summary. Therefore, it is useful when you need actual cases, demonstrations, interviews, or other audiovisual materials for a certain domain, when you need lectures or tutorials, or when you need product reviews or usage tips. However, as mentioned earlier, it is only useful for videos with transcripts.
Search Engine 5:
>> name: BraveSearch
>> description: BraveSearch is ideal for comprehensive searches across a wide range of topics, providing results that are both directly and indirectly related to the query or keywords. It offers a broad spectrum of information, including diverse perspectives and the latest updates, making it perfect for queries that require a variety of viewpoints and up-to-date information. BraveSearch delivers a balanced mix of reliable, high-quality sources and user-generated content such as blogs, social media, and forums. By crawling and indexing a vast number of web pages, it ensures extensive coverage and delivers well-rounded search results.
"""

high_level_outline_chain = (
    {
        "derived_queries": itemgetter("derived_queries"),
        "inner_monologue": itemgetter("inner_monologue"),
        "original_question": itemgetter("original_question"),
    }
    | high_level_outline_prompt.partial(additional_instructions="",
                                        search_engines=search_engines_description,
                                        additional_restrictions="10. ALWAYS USE 'HighLevelDocument_Outline' Tool, so the user know your high-level-outline! Take a careful at the schema of the tool, and use the tool.")
    | high_level_outline_llm.with_structured_output(HighLevelDocument_Outline)
    | high_level_outline_parser

)

# This is for generate_search_query_plans stage, You can freely modify it!
tool_description_with_search_query_tip = """Tool 1:
>> name: tavily_search_results_json
>> description: Use this tool when you need reliable searches on a wide range of topics. It performs deep searches focusing on materials from trustworthy sites and is suitable for most general searches. Tavily excels in searching for topics with low volatility or when detailed content is required. It is useful for academic research, in-depth information on specific domains, historical facts, or areas with low variability, as well as when collecting quotes or data from reliable sources. The searches are highly relevant to the query or keywords, resulting in targeted and specialized results. However, the scope of the provided information may be limited to directly related content. 
>> search query tip: To find in-depth information on a specific domain, field, or knowledge, it is good to use 'search terms' centered around related core concepts, principles, and examples. 'Search keywords' are also effective.
Tool 2:
>> name: arxiv_search
>> description: arXiv is a search engine that shares the latest research in various and wide-ranging scientific fields such as physics, mathematics, computer science, and biology. It is primarily used when highly deep and specialized knowledge, in-depth information, or the latest research techniques and methodologies are needed for a particular topic or domain. It is recommended to selectively utilize arXiv searches only when very professional and technical content is required. The return results basically provide a summary and extraction of specific content by the LLM for the full text of the papers found through the arXiv search.
>> search query tip: To identify and collect information on scientific fields or the latest research, 'search terms' consisting of core 'keywords' directly related to the topic are good. However, avoid using overly professional or technical terms, and select search terms based on a basic understanding and background knowledge of the relevant field for effective results.
Tool 3:
>> name: youtube_search
>> description: It is generally optimized for video searches. However, it is not a typical video search but an API-style search. For videos that support transcripts, the LLM looks at the transcript and extracts content directly related to the search query. The return results include the video title, view count, upload date, content extracted by the LLM about the video, and a summary. Therefore, it is useful when you need actual cases, demonstrations, interviews, or other audiovisual materials for a certain domain, when you need lectures or tutorials, or when you need product reviews or usage tips. However, as mentioned earlier, it is only useful for videos with transcripts.
>> search query tip: To find audiovisual materials or tutorials for a specific domain, field, or knowledge, it is good to use 'search terms' combined with 'search keywords'.
Tool 4:
>> name: wikipedia
>> description: It is an online encyclopedia covering a wide range of topics. It allows you to quickly collect basic information on concepts, people, events, places, etc. from various fields. As it is an online encyclopedia, it is written and edited by many people online. Although efforts are made to maintain the latest information and neutrality of the content, verification with other reliable searches is required. It is suitable for quickly grasping an overview of a topic or domain, confirming the definition of a term, or as a starting point for in-depth research. It contains a lot of information that helps build general common sense and knowledge rather than academic research. However, there may be cases where there are no results when searching for a specific domain or topic. The return results basically provide a pair of the Wikipedia page name for a specific topic and an overall summary of the page content.
>> search query tip: To find basic information such as concepts, definitions, and features, 'search keywords' should consist of words directly related to the topic.
Tool 5:
>> name: brave_search_results_json
>> description: Use Brave Search when you need a broad and comprehensive search across a wide range of websites and domains. It is particularly effective for finding the most up-to-date information on current events, trending topics, and rapidly evolving fields. Brave Search crawls and indexes billions of webpages to provide extensive coverage. While it may not always have the same depth as Tavily for academic or highly specialized topics, its strengths lie in its vast reach and ability to surface relevant content from a huge variety of sources. This makes it ideal for queries where a diversity of perspectives and the most current information is desired. Brave Search is also a strong choice when you want a balance of both reliable, high-quality sources and more informal user-generated content like blog posts, social media, forums etc. It provides a well-rounded view. In addition to webpages, Brave Search is effective at finding relevant images, videos, news articles, and other media related to the search. It's useful for things like comprehensive overviews of topics, research on current affairs and pop culture, comparison of different products/services, discovering a range of opinions on issues, and finding real-world examples or applications of concepts.
>> search query tip: For the most relevant results on Brave Search, use specific but concise keyphrases that capture the core elements of your query. Including 1-2 of the most essential keywords is usually sufficient.
"""


generate_search_query_plans_chain = (
    {
        "original_question": itemgetter("original_question"),
        "inner_monologue": itemgetter("inner_monologue"),
        "high_level_outline": itemgetter("high_level_outline")
    }
    | generate_search_query_plans_prompt.partial(
        additional_restrictions="7. ALWAYS USE 'HighLevelDocument_Plan' Tool, so the user know your plan! Take a careful at the schema of the tool, and use the tool.\n8. **ALWAYS USE ENGLISH**",
        tools=tool_description_with_search_query_tip
        )
    | generate_search_query_plans_llm.with_structured_output(HighLevelDocument_Plan).with_fallbacks([generate_search_query_plans_llm.with_structured_output(HighLevelDocument_Plan)] * 5)
    | generate_search_query_plans_parser
)


class THLO_state(TypedDict):
    original_question: str
    derived_queries: str
    inner_monologue: Thought
    high_level_outline: HighLevelDocument_Outline
    search_query_engine_plan: HighLevelDocument_Plan
    evaluation_criteria: str


async def thought_node(state: THLO_state):
    """Thought stage"""
    print("---THLO STATE: THOUGHT NODE---")
    original_question = state["original_question"]
    derived_queries = state["derived_queries"]
    thought_result = await thought_chain.ainvoke({
        "original_question": original_question,
        "derived_queries": derived_queries
    })
    return thought_result


async def high_level_outline_node(state: THLO_state):
    """Based on thought result, generate high-level-outline"""
    print('---THLO STATE: HIGH_LEVEL_OUTLINE_NODE---')
    original_question = state["original_question"]
    derived_queries = state["derived_queries"]
    inner_monologue = state['inner_monologue']
    high_level_outline_result = await high_level_outline_chain.ainvoke({
        'original_question': original_question,
        'derived_queries': derived_queries,
        'inner_monologue': inner_monologue.as_str(),
    })
    return {
        "inner_monologue": inner_monologue,
        "high_level_outline": high_level_outline_result
    }


async def generate_search_query_node(state: THLO_state):
    """Based on thought result, and high-level-outline, generate search query and selected engine.
    It's look like Plan-and-Execute architecture's Plan stage.
    """
    print('---THLO STATE: GENERATE SEARCH QUERY NODE---')
    original_question = state["original_question"]
    inner_monologue = state['inner_monologue']
    high_level_outline = state['high_level_outline']['high_level_outline']
    evaluation_criteria = high_level_outline.evaluation_criteria

    generate_search_query_plans_chain_with_fallback = generate_search_query_plans_chain.with_fallbacks([generate_search_query_plans_chain] * 5)
    generate_search_query_result = await generate_search_query_plans_chain_with_fallback.ainvoke({
        "original_question": original_question,
        "inner_monologue": inner_monologue.as_str(),
        "high_level_outline": high_level_outline.as_str()
    })
    return {
        "search_query_engine_plan": generate_search_query_result['search_query_engine_plan'],
        "evaluation_criteria": evaluation_criteria
    }


def get_THLO_Graph():
    workflow = StateGraph(THLO_state)
    workflow.add_node("thought", thought_node)
    workflow.add_node("high_level_outline_node", high_level_outline_node)
    workflow.add_node("generate_search_query", generate_search_query_node)
    workflow.add_edge("thought", "high_level_outline_node")
    workflow.add_edge("high_level_outline_node", "generate_search_query")
    workflow.set_entry_point("thought")
    workflow.set_finish_point("generate_search_query")
    THLO_Graph = workflow.compile().with_config(run_name="Think High Level Outline(THLO)")
    return THLO_Graph

