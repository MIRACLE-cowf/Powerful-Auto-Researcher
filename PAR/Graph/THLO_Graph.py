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
llm = get_anthropic_model(model_name="haiku")


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


thought_chain = thought_prompt | llm.with_structured_output(Thought) | thought_output_parser
high_level_outline_chain = (
    {
        "derived_queries": itemgetter("derived_queries"),
        "inner_monologue": itemgetter("inner_monologue"),
        "original_question": itemgetter("original_question"),
    }
    | high_level_outline_prompt
    | llm.with_structured_output(HighLevelDocument_Outline)
    | high_level_outline_parser

)
generate_search_query_plans_chain = (
        {
        "original_question": itemgetter("original_question"),
        "inner_monologue": itemgetter("inner_monologue"),
        "high_level_outline": itemgetter("high_level_outline")
    }
        | generate_search_query_plans_prompt
        | llm.with_structured_output(HighLevelDocument_Plan)
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
    generate_search_query_result = generate_search_query_plans_chain.invoke({
        "original_question": original_question,
        "inner_monologue": inner_monologue.as_str(),
        "high_level_outline": high_level_outline.as_str()
    })
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