from operator import itemgetter
from typing import TypedDict, Dict

from langchain import hub
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph

from CustomHelper.THLO_helper import Thought, HighLevelDocument_Outline, HighLevelDocument_Plan
from CustomHelper.load_model import get_anthropic_model

thought_prompt = hub.pull("miracle/par_thought_prompt_public")
high_level_outline_prompt = hub.pull("miracle/par_high_level_outline_prompt_public")
generate_search_query_plans_prompt = hub.pull("miracle/par_generate_search_query_prompt_public")


# This THLO stage is very important and powerful stage in PAR architecture, so we try to use high-quality model.
# Note: But it can also pretty good with "haiku" and "sonnet"
# Just your judgement. But I'm use "opus" at "high level outline" stage.
thought_llm = get_anthropic_model(model_name="sonnet")
high_level_outline_llm = get_anthropic_model(model_name="opus")

generate_search_query_plans_llm = get_anthropic_model(model_name="sonnet")
generate_search_query_plans_fallback_final = get_anthropic_model(model_name="opus")


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
high_level_outline_chain = (
    {
        "derived_queries": itemgetter("derived_queries"),
        "inner_monologue": itemgetter("inner_monologue"),
        "original_question": itemgetter("original_question"),
    }
    | high_level_outline_prompt.partial(additional_instructions="", additional_restrictions="7. ALWAYS USE 'HighLevelDocument_Outline' Tool, so the user know your high-level-outline!\n8. Take a careful at the schema of the tool, and use the tool.")
    | high_level_outline_llm.with_structured_output(HighLevelDocument_Outline)
    | high_level_outline_parser

)

# This is for generate_search_query_plans stage, You can freely modify it!
tool_description = """Tool 1:
>> name: tavily_search_results_json
>> description: A powerful and comprehensive search engine that should be used as the primary tool for information gathering. It performs a broad Google search and then uses an LLM to summarize the actual content of the web pages, providing a concise overview of the main points from various sources quickly and comprehensively. This makes it effective for both broad and specific searches. It is recommended to use this tool for the majority of your searches.
Tool 2:
>> name: arXiv_search
>> description: A specialized tool for finding and summarizing various papers on arXiv. Use this tool when you need to collect technical information or insights from paper literacture, such as key experimental results, insights, or expert opinions that my not be covered by general search engines(tavily_search_results_json) or Wikipedia.
Tool 3:
>> name: youtube_search
>> description: A tool for searching YouTube videos and obtaining information about them. It uses an LLM to summarize and extract information based on the actual transcripts of the YouTube videos(If there has transcript). Therefore, it is powerful when you need to gather information from video sources or recommend videos to user.
Tool 4:
>> name: wikipedia
>> description: A reliable source for general information on a wide range of topics and specific subjects. Use this tool to gather additional context or background information to supplement the summaries from tavily_search_results_json. It returns the title and summary of the full content for the top 3 most relevant Wikipedia pages for a given search query. However, it should not be used as the primary search tool.
"""

generate_search_query_plans_chain = (
        {
        "original_question": itemgetter("original_question"),
        "inner_monologue": itemgetter("inner_monologue"),
        "high_level_outline": itemgetter("high_level_outline")
    }
        | generate_search_query_plans_prompt.partial(additional_restrictions="4. ALWAYS USE 'HighLevelDocument_Plan' Tool, so the user know your plan!\n5. Take a careful at the schema of the tool, and use the tool.", tools=tool_description)
        | generate_search_query_plans_llm.with_structured_output(HighLevelDocument_Plan)
        | generate_search_query_plans_parser
)


# I found few bugs in generate search query plans stage, so try to handle fallback.
generate_search_query_plans_chain_for_first_fallback = (
    {
        "original_question": itemgetter("original_question"),
        "inner_monologue": itemgetter("inner_monologue"),
        "high_level_outline": itemgetter("high_level_outline")
    }
    | generate_search_query_plans_prompt.partial(
        additional_restrictions="4. ALWAYS USE 'HighLevelDocument_Plan' Tool, so the user know your plan!\n5. Take a careful at the schema of the tool, and use the tool.",
        tools=tool_description
    )
    | generate_search_query_plans_llm.with_structured_output(HighLevelDocument_Plan)
    | generate_search_query_plans_parser
)
generate_search_query_plans_chain_final_fallback = (
    {
        "original_question": itemgetter("original_question"),
        "inner_monologue": itemgetter("inner_monologue"),
        "high_level_outline": itemgetter("high_level_outline")
    }
    | generate_search_query_plans_prompt.partial(
        additional_restrictions="4. ALWAYS USE 'HighLevelDocument_Plan' Tool, so the user know your plan!\n5. Take a careful at the schema of the tool, and use the tool.",
        tools=tool_description
    )
    | generate_search_query_plans_fallback_final.with_structured_output(HighLevelDocument_Plan)
    | generate_search_query_plans_parser
)


class THLO_state(TypedDict):
    original_question: str
    derived_queries: str
    inner_monologue: Thought
    high_level_outline: HighLevelDocument_Outline
    search_query_engine_plan: HighLevelDocument_Plan


def thought_node(state):
    """Thought stage"""
    print("---STATE: THOUGHT NODE---")
    original_question = state["original_question"]
    derived_queries = state["derived_queries"]
    thought_result = thought_chain.invoke({
        "original_question": original_question,
        "derived_queries": derived_queries
    })
    return thought_result


def high_level_outline_node(state):
    """Based on thought result, generate high-level-outline"""
    print('---STATE: HIGH_LEVEL_OUTLINE_NODE---')
    original_question = state["original_question"]
    derived_queries = state["derived_queries"]
    inner_monologue = state['inner_monologue']
    high_level_outline_result = high_level_outline_chain.invoke({
        'original_question': original_question,
        'derived_queries': derived_queries,
        'inner_monologue': inner_monologue.as_str()
    })
    print('---HIGH LEVEL_OUTLINE_NODE---')
    return {
        "inner_monologue": inner_monologue,
        "high_level_outline": high_level_outline_result
    }


def generate_search_query_node(state):
    """Based on thought result, and high-level-outline, generate search query and selected engine.
    It's look like Plan-and-Execute architecture's Plan stage.
    """
    print('---STATE: GENERATE SEARCH QUERY NODE---')
    original_question = state["original_question"]
    inner_monologue = state['inner_monologue']
    high_level_outline = state['high_level_outline']['high_level_outline']
    generate_search_query_plans_chain_with_final_fallback = generate_search_query_plans_chain_for_first_fallback.with_fallbacks([generate_search_query_plans_chain_final_fallback])
    generate_search_query_plans_chain_with_fallback = generate_search_query_plans_chain.with_fallbacks([generate_search_query_plans_chain_with_final_fallback])
    generate_search_query_result = generate_search_query_plans_chain_with_fallback.invoke({
        "original_question": original_question,
        "inner_monologue": inner_monologue.as_str(),
        "high_level_outline": high_level_outline.as_str()
    })
    print('---GENERATE SEARCH QUERY NODE---')
    print(f"GENERATE SEARCH QUERY:\n{generate_search_query_result['search_query_engine_plan'].as_str()}")
    return generate_search_query_result


workflow = StateGraph(THLO_state)
workflow.add_node("thought", thought_node)
workflow.add_node("high_level_outline_node", high_level_outline_node)
workflow.add_node("generate_search_query", generate_search_query_node)
workflow.add_edge("thought", "high_level_outline_node")
workflow.add_edge("high_level_outline_node", "generate_search_query")
workflow.set_entry_point("thought")
workflow.set_finish_point("generate_search_query")
THLO_Graph = workflow.compile().with_config(run_name="Think High Level Outline(THLO)")