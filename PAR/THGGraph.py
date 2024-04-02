from operator import itemgetter
from typing import TypedDict, Dict

from langchain import hub
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph

from CustomHelper.Helper import parse_search_result
from CustomHelper.load_model import get_anthropic_model

thought_prompt = hub.pull("miracle/par_thought_prompt_public")
high_level_outline_prompt = hub.pull("miracle/par_high_level_outline_prompt_public")
generate_search_query_prompt = hub.pull("miracle/par_generate_search_query_prompt_public")
llm = get_anthropic_model(model_name="haiku")


def thought_output_parser(thought: str) -> dict:
    return {
        "keys": {
            "inner_monologue": thought
        }
    }


thought_chain = thought_prompt | llm.bind(stop=["</thoughts"]) | StrOutputParser() | thought_output_parser
high_level_outline_chain = (
    {
        "derived_queries": itemgetter("derived_queries"),
        "inner_monologue": itemgetter("inner_monologue"),
        "original_question": itemgetter("original_question"),
    }
    | high_level_outline_prompt
    | llm.bind(stop=["</document_generation_plan>"])
    | StrOutputParser()
)
generate_search_query_chain = (
    {
        "original_question": itemgetter("original_question"),
        "inner_monologue": itemgetter("inner_monologue"),
        "high_level_outline": itemgetter("high_level_outline")
    }
    | generate_search_query_prompt
    | llm.bind(stop=["</search_queries_output>"])
    | StrOutputParser()
)


class State(TypedDict):
    original_question: str
    derived_queries: str
    keys: Dict[str, any]


def thought_node(state):
    print("---STATE: THOUGHT NODE---")
    original_question = state["original_question"]
    derived_queries = state["derived_queries"]
    thought_result = thought_chain.invoke({
        "original_question": original_question,
        "derived_queries": derived_queries
    })
    return thought_result


def high_level_outline_node(state):
    print('---STATE: HIGH_LEVEL_OUTLINE_NODE---')
    state_dict = state["keys"]
    original_question = state["original_question"]
    derived_queries = state["derived_queries"]
    inner_monologue = state_dict['inner_monologue']
    high_level_outline_result = high_level_outline_chain.invoke({
        'original_question': original_question,
        'derived_queries': derived_queries,
        'inner_monologue': inner_monologue
    })

    return {
        "keys": {
            "inner_monologue": inner_monologue,
            "high_level_outline": high_level_outline_result
        }
    }


def generate_search_query_node(state):
    print('---STATE: GENERATE SEARCH QUERY NODE---')
    state_dict = state["keys"]
    original_question = state["original_question"]
    inner_monologue = state_dict['inner_monologue']
    high_level_outline = state_dict['high_level_outline']
    generate_search_query_result = generate_search_query_chain.invoke({
        "original_question": original_question,
        "inner_monologue": inner_monologue,
        "high_level_outline": high_level_outline
    })
    generate_search_query_result = parse_search_result(generate_search_query_result)
    return {
        "keys": {
            'generation': generate_search_query_result
        }
    }


workflow = StateGraph(State)
workflow.add_node("thought", thought_node)
workflow.add_node("high_level_outline", high_level_outline_node)
workflow.add_node("generate_search_query", generate_search_query_node)
workflow.add_edge("thought", "high_level_outline")
workflow.add_edge("high_level_outline", "generate_search_query")
workflow.set_entry_point("thought")
workflow.set_finish_point("generate_search_query")
THG_part = workflow.compile().with_config(run_name="Think High Level Outline Draft")