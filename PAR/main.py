import asyncio
import re
from typing import TypedDict, Dict, Any, List

from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_text_splitters import CharacterTextSplitter
from langgraph.graph import StateGraph, END

from Agent_Team.Member.Common_Search_AgentGraph import TavilySearchAgentGraph
from Agent_Team.Project_Manager_Agent import get_pm_graph, get_pm_graph_mermaid
from CustomHelper.Helper import generate_doc_result, generate_final_doc_results, retry_with_delay_async
from CustomHelper.THLO_helper import SectionPlan
from CustomHelper.load_model import get_anthropic_model
from Graph.THLO_Graph import get_THLO_Graph
from Single_Chain.ConclustionChain import conclusion_chain
from Single_Chain.FastSearchChain import get_fast_search_result
from Single_Chain.GenerateFinalAnswer import get_generate_final_answer_chain
from Single_Chain.GenerateNewPrompt import GenerateNewPromptFunc
from Single_Chain.GradingDocumentsChain import grading_documents_chain
from Single_Chain.MultiQueryChain import multi_query_chain, DerivedQueries
from Single_Chain.Retrieve_Vector_DB import search_vector_store
from Util.PAR_Helper import setup_new_document_format, parse_result_to_document_format, \
    save_document_to_md
from Util.Retriever_setup import parent_retriever
from Util.console_controller import print_warning_message, clear_console, print_see_you_again


class PAR_Final_RespondSchema(BaseModel):
    """This tool allows you to let the user know your answer."""
    background: str = Field(description="Write main background based on provided documents")
    introduction: str = Field(description="Write main introduction based on provided documents")
    excerpts: str = Field(description="Write some important excerpts from the provided documents")
    insights: str = Field(description="Write your thoughts and insights based on provided documents")
    direct_response: str = Field(description="Write your final direct response based on provided documents")
    conclusion: str = Field(description="Write your conclusion based on provided documents")
    any_helpful: str = Field(description="If there is any useful or helpful information that can help the user in the future based on the provided documents.")


class RAG_State(TypedDict):
    user_question: str
    original_query: str
    derived_queries: DerivedQueries
    document_title: str
    document_description: str
    fast_search_results: str
    search_continue: bool
    keys: Dict[str, Any]


async def generate_new_prompt_node(state: RAG_State):
    print("---MAIN STATE: GENERATE NEW PROMPT IN---")
    original_query = state["user_question"]
    new_question_prompt = await GenerateNewPromptFunc(user_input=original_query)
    print("---MAIN STATE: GENERATE NEW PROMPT OUT---")

    return {
        'original_query': new_question_prompt,
    }


async def multi_query_generator_node(state: RAG_State):
    print("---MAIN STATE: MULTI QUERY GENERATOR IN---")
    original_query = state["original_query"]
    multi_query_result = await multi_query_chain(model=get_anthropic_model()).ainvoke({"question": original_query})
    print("---MAIN STATE: MULTI QUERY GENERATOR OUT---")

    return {
        'derived_queries': multi_query_result
    }


async def retrieve_node(state: RAG_State):
    print("---MAIN STATE: RETRIEVE IN VECTOR DB---")
    multi_queries = state['derived_queries']
    retrieve_result = await search_vector_store(
        multi_query=multi_queries,
        retriever=parent_retriever
    )
    print("---MAIN STATE: RETRIEVE OUT VECTOR DB---")

    return {
        "keys": {
            "retrieve_result": retrieve_result
        }
    }


async def grade_document(state: RAG_State):
    print("---MAIN STATE: GRADING DOCUMENTS START---")
    state_dict = state["keys"]
    retrieve_result = state_dict['retrieve_result']
    index = 1
    grading_results = {}

    grading_chain = grading_documents_chain(model=get_anthropic_model())

    # grading_chain_input = []
    # for new_query, documents in retrieve_result.items():
    #     doc_str = generate_doc_result(documents)
    #     grading_chain_input.append({'question': new_query, 'documents': doc_str})
    #
    # _grade_results = await grading_chain.abatch(inputs=grading_chain_input)
    # print(_grade_results)
    # grade_count = 0
    # for grade in _grade_results:
    #     if grade.grade.binary_score:
    #         final_doc_results = ""
    #         final_doc_results += generate_final_doc_results()
    #         grade_count += 1
    #     else:
    #         grading_results[new_query] = "needsearch"

    for new_query, documents in retrieve_result.items():
        doc_str = generate_doc_result(documents)

        grade_result = await grading_chain.ainvoke({
            "question": new_query,
            "documents": doc_str
        })

        grade = grade_result.binary_score

        if grade == 'yes':
            print(f"---{new_query} GRADE: DOCUMENT RELEVANT---")
            final_doc_results = ""
            final_doc_results += generate_final_doc_results(documents, index)
            index += 3
            grading_results[new_query] = final_doc_results
        else:
            print(f"---{new_query} GRADE: DOCUMENT NOT RELEVANT---")
            grading_results[new_query] = "needsearch"

    print("---MAIN STATE: GRADING DOCUMENTS DONE---")
    return {
        "keys": {
            "grading_results": grading_results
        }
    }


def decide_to_generate(state: RAG_State):
    print("---MAIN STATE: DECIDE to GENERATE---")
    state_dict = state["keys"]
    grading_results = state_dict["grading_results"]

    cnt = 0
    for index, (query, result) in enumerate(grading_results.items(), start=1):
        if result == "needsearch":
            cnt += 1

    print(f"needsearch count: {cnt}")

    if cnt > 0:
        print("---MAIN STATE: DECIDE THLO STAGE---")
        return "think_high_level_outline"
    else:
        print("---MAIN STATE: DECIDE GENERATE FINAL ANSWER---")
        return "generate"


async def think_high_level_outline_node(state: RAG_State):
    print('---MAIN STATE: THINK HIGH LEVEL OUTLINE GRAPH START---')
    state_dict = state["keys"]
    grading_results = state_dict["grading_results"]
    original_query = state["original_query"]
    derived_queries = ""
    for query, _ in grading_results.items():
        derived_queries += query + "\n"

    THLO_Graph = get_THLO_Graph()
    high_level_outline = await THLO_Graph.ainvoke({
        "original_question": original_query,
        'derived_queries': derived_queries
    })
    print('---MAIN STATE: THINK HIGH LEVEL OUTLINE GRAPH END---')
    return {
        'high_level_outline': high_level_outline["search_query_engine_plan"],
        'evaluation_criteria': high_level_outline["evaluation_criteria"],
    }


async def fast_search(state: RAG_State):
    print("---MAIN STATE: FAST SEARCH IN---")
    fast_search_results = await get_fast_search_result(state["original_query"])
    print("---MAIN STATE: FAST SEARCH OUT---")

    return {
        "fast_search_results": fast_search_results,
    }


async def parallel_execution_node(state: RAG_State):
    print("---MAIN STATE: PARALLEL EXECUTION IN---")
    fast_search_task = asyncio.create_task(fast_search(state))
    thlo_task = asyncio.create_task(think_high_level_outline_node(state))

    _fast_search_result = await fast_search_task
    print(f"fast search result: {_fast_search_result['fast_search_results']}")
    state["fast_search_results"] = _fast_search_result['fast_search_results']
    user_input = input("Fast search completed. Continue with Deep Search? (y/n) ")
    if user_input.lower() != 'y':
        state["search_continue"] = False
        thlo_task.cancel()
        return {**state}

    _thlo_graph_result = await thlo_task
    print(_thlo_graph_result)
    state["keys"] = {
        "high_level_outline": _thlo_graph_result["high_level_outline"],
        "evaluation_criteria": _thlo_graph_result["evaluation_criteria"],
    }
    state["search_continue"] = True
    print("---MAIN STATE: PARALLEL EXECUTION COMPLETE---")

    return {
        **state,
    }


async def composable_search_node(state: RAG_State):
    print('---MAIN STATE: COMPOSABLE SEARCH NODE---')
    state_dict = state["keys"]
    generation_result = state_dict["high_level_outline"]
    original_question = state["original_query"]

    document_title = generation_result.title
    document_description = generation_result.objective
    sections = generation_result.sections

    full_document_without_conclusion = setup_new_document_format(document_title=document_title, document_description=document_description, original_question=original_question)

    last_conclusion_section = sections[-1]

    search_graph_batch_results = []

    def prepare_batch_input_data(_sections: List[SectionPlan]) -> list:
        return [{'input': _section.as_str(), 'search_result': "", 'order': _section.order, 'section_basic_info': _section.as_str_for_basic_info()} for _section in _sections]

    search_graph_batch_input = prepare_batch_input_data(sections[:-1])
    project_manager_graph = get_pm_graph()
    print('---AGENT BATCH START---')
    # (test)Now we are going use batch
    _search_graph_batch_results = await project_manager_graph.abatch(search_graph_batch_input, {'recursion_limit': 100})
    search_graph_batch_results.extend(_search_graph_batch_results)
    print('---AGENT BATCH END---')

    ordered_results = {search_graph_result['order']: search_graph_result for search_graph_result in search_graph_batch_results}

    for order in sorted(ordered_results.keys()):
        print(f'---ORDER: {order}---')
        search_graph_result = ordered_results[order]
        print(search_graph_result)

        if search_graph_result["final_section_document"]:
            document = search_graph_result["final_section_document"]
        else:
            output = search_graph_result["agent_output"].return_values["output"]
            result_match = re.search(r"<result>(.*?)</result>", output, re.DOTALL)
            if result_match:
                document = result_match.group(1).strip()
            else:
                document = output
        # document = search_graph_result["final_section_document"]
        full_document_without_conclusion += parse_result_to_document_format(document=document)
    print('---GENERATE DOCUMENT DRAFT DONE---')

    conclusion = await conclusion_chain(previous_sections_info=full_document_without_conclusion, conclusion_section_info=last_conclusion_section.as_str())
    full_document_draft_display = full_document_without_conclusion + '\n\n\n' + conclusion

    return {
        'document_title': document_title,
        'document_description': document_description,
        'keys': {
            'full_document_draft_display': full_document_draft_display
        }
    }


async def generate(state: RAG_State):
    print("---GENERATE---")
    # print(f"state: {state}")
    state_dict = state["keys"]
    user_question = state["user_question"]
    question = state["original_query"]
    documents = state_dict.get("grading_results", {})
    document_title = state.get("document_title", "")
    full_documents_display = state_dict.get("full_document_draft_display", "")

    documents_for_prompt = ""
    if full_documents_display:
        # No Need to wait for save
        asyncio.ensure_future(save_document_to_md(full_document=full_documents_display, document_title=document_title))

        # save_document_to_md(full_document=full_documents_display, document_title=document_title)
        documents_for_prompt = full_documents_display
        user_response = input('[y/n] Would you want to save this document in Vector Store?: ')
        if user_response == 'y':
            text_splitter = CharacterTextSplitter(
                separator="\n\n",
                chunk_size=4000,
                chunk_overlap=400,
                length_function=len,
                is_separator_regex=False
            )
            # Will be use it soon!
            # docs = text_splitter.create_documents([documents_for_prompt])
            # key = question + "_final_document"
            # for index, doc in enumerate(docs, start=1):
            #     mongodb_store.mset([(key, doc)])
            #     parent_retriever.add_documents([doc], ids=key+f"_{index}")
            print("DOCUMENT SAVED AT VECTORSTORE & MONGODB SUCCESSFULLY!")
    else:
        for query, document in documents.items():
            documents_for_prompt += document

    rag_chain = get_generate_final_answer_chain()
    generation = await retry_with_delay_async(
        chain=rag_chain,
        input={
            'question': user_question,
            'documents': documents_for_prompt
        },
        max_retries=3,
        delay_seconds=60.0
    )

    return {
        "keys": {
            "generation": generation,
            "full_documents": documents_for_prompt
        }
    }


def decide_continue(state: RAG_State):
    print(state)
    if state['search_continue'] is True:
        return "True"
    else:
        return "False"


def build_graph():
    workflow = StateGraph(RAG_State)
    # add node
    workflow.add_node("transform_new_query", generate_new_prompt_node)
    # workflow.add_node("fast_search", fast_search_node)
    workflow.add_node("multi_query_generator", multi_query_generator_node)
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("grade_documents", grade_document)

    workflow.add_node("parallel_execution", parallel_execution_node)

    # workflow.add_node("think_high_level_outline", think_high_level_outline_node)
    workflow.add_node("composable_search", composable_search_node)
    workflow.add_node("generate", generate)

    workflow.set_entry_point("transform_new_query")

    # add edge
    # workflow.add_edge("transform_new_query", "fast_search")
    workflow.add_edge("transform_new_query", "multi_query_generator")
    workflow.add_edge("multi_query_generator", "retrieve")
    workflow.add_edge("retrieve", "grade_documents")
    # conditional edges
    workflow.add_conditional_edges(
        "grade_documents",
        decide_to_generate,
        {
            "think_high_level_outline": "parallel_execution",
            "generate"                : "generate"
        }
    )
    workflow.add_conditional_edges(
        "parallel_execution",
        decide_continue,
        {
            "True": "composable_search",
            "False": END
        }
    )
    workflow.add_edge("generate", END)
    # workflow.add_edge("think_high_level_outline", "composable_search")
    workflow.add_edge("composable_search", "generate")
    return workflow.compile()


def get_graph_mermaid():
    app = build_graph()
    try:
        print("Main Graph Mermaid")
        print(app.get_graph(xray=True).draw_mermaid())
        # display(Image(app.get_graph(xray=True).draw_mermaid_png()))
    except Exception as e:
        print(f"pass: {e}")
        pass


async def run_graph():
    app = build_graph()
    print_warning_message()
    user_input = input("[y/n]:")

    if user_input == 'y':
        clear_console()
        user_query = input("What are you looking for?: ")
        inputs = {
            "user_question": user_query
        }

        result = await app.ainvoke(inputs)
        print(result)
        print("####DOCUMENT####")
        print(result['keys']['full_documents'])
        print("----------------------------")

        final_result = result['keys']['generation']
        print(f"Final Result: \n\n{final_result}")
        # print(f"Final Result: {final_result.direct_response}\n"
        #       f"\n###BACKGROUND###\n{final_result.background}\n"
        #       f"###INTRODUCTION###\n{final_result.introduction}\n"
        #       f"###EXCERPTS###\n{final_result.excerpts}\n"
        #       f"###INSIGHTS###\n{final_result.insights}\n"
        #       f"###CONCLUSTION###\n{final_result.conclusion}\n"
        #       f"###ANY_HELPFUL###\n{final_result.any_helpful}\n")

    else:
        clear_console()
        print_see_you_again()


def get_all_graph():
    get_graph_mermaid()
    search_graph = TavilySearchAgentGraph()
    search_graph.get_search_agent_graph_mermaid()
    get_pm_graph_mermaid()


if __name__ == "__main__":
    # get_all_graph()
    asyncio.run(run_graph())