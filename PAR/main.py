from typing import TypedDict, Dict

from langchain import hub
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_text_splitters import CharacterTextSplitter
from langgraph.graph import StateGraph, END

from Agent_Team.Project_Manager_Agent import project_manager_graph
from CustomHelper.Helper import generate_doc_result, generate_final_doc_results
from CustomHelper.load_model import get_anthropic_model
from Graph.THLO_Graph import THLO_Graph
from Single_Chain.ConclustionChain import conclusion_chain
from Single_Chain.GradingDocumentsChain import grading_documents_chain
from Single_Chain.MultiQueryChain import multi_query_chain, DerivedQueries
from Single_Chain.Retrieve_Vector_DB import search_vector_store
from Util.PAR_Helper import setup_new_document_format, parse_result_to_document_format, \
	save_document_to_md
from Util.Retriever_setup import parent_retriever
from Util.console_controller import clear_console, print_warning_message, print_see_you_again

generate_prompt = hub.pull("miracle/par_generation_prompt")


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
    original_query: str
    derived_queries: DerivedQueries
    document_title: str
    document_description: str
    keys: Dict[str, any]


def multi_query_generator_node(state: RAG_State):
    print("---MAIN STATE: MULTI QUERY GENERATOR IN---")
    original_query = state["original_query"]
    multi_query_result = multi_query_chain(model=get_anthropic_model()).invoke({"question": original_query})
    print("---MAIN STATE: MULTI QUERY GENERATOR OUT---")

    return {
        'derived_queries': multi_query_result
    }


def retrieve_node(state: RAG_State):
    print("---MAIN STATE: RETRIEVE IN VECTOR DB---")
    multi_queries = state['derived_queries']
    retrieve_result = search_vector_store(
        multi_query=multi_queries,
        retriever=parent_retriever
    )
    print("---MAIN STATE: RETRIEVE OUT VECTOR DB---")

    return {
        "keys": {
            "retrieve_result": retrieve_result
        }
    }


def grade_document(state: RAG_State):
    print("---MAIN STATE: GRADING DOCUMENTS START---")
    state_dict = state["keys"]
    retrieve_result = state_dict['retrieve_result']
    index = 1
    grading_results = {}

    grading_chain = grading_documents_chain(model=get_anthropic_model())

    for new_query, documents in retrieve_result.items():
        doc_str = generate_doc_result(documents)

        grade_result = grading_chain.invoke({
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


def think_high_level_outline_node(state: RAG_State):
    print('---MAIN STATE: THINK HIGH LEVEL OUTLINE GRAPH START---')
    state_dict = state["keys"]
    grading_results = state_dict["grading_results"]
    original_query = state["original_query"]
    derived_queries = ""
    for query, _ in grading_results.items():
        derived_queries += query + "\n"

    high_level_outline = THLO_Graph.invoke({
        "original_question": original_query,
        'derived_queries': derived_queries
    })
    print('---MAIN STATE: THINK HIGH LEVEL OUTLINE GRAPH END---')
    return {
        "keys": {
            'high_level_outline': high_level_outline["search_query_engine_plan"],
            'evaluation_criteria': high_level_outline["evaluation_criteria"],
        }
    }


def composable_search_node(state: RAG_State):
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

    def prepare_batch_input_data(_sections) -> list:
        return [{'input': _section.as_str(), 'search_result': "", 'order': _section.order} for _section in _sections]


    search_graph_batch_input = prepare_batch_input_data(sections[:-1])
    print('---AGENT BATCH START---')
    # (test)Now we are going use batch
    _search_graph_batch_results = project_manager_graph.batch(search_graph_batch_input, {'recursion_limit': 100})
    search_graph_batch_results.extend(_search_graph_batch_results)
    print('---AGENT BATCH END---')

    ordered_results = {search_graph_result['order']: search_graph_result for search_graph_result in search_graph_batch_results}

    for order in sorted(ordered_results.keys()):
        print(f'---ORDER: {order}---')
        search_graph_result = ordered_results[order]
        document = search_graph_result["final_section_document"]
        full_document_without_conclusion += parse_result_to_document_format(document=document)
    print('---GENERATE DOCUMENT DRAFT DONE---')

    conclusion = conclusion_chain(previous_sections_info=full_document_without_conclusion, conclusion_section_info=last_conclusion_section.as_str())
    full_document_draft_display = full_document_without_conclusion + '\n\n\n' + conclusion

    return {
        'document_title': document_title,
        'document_description': document_description,
        'keys': {
            'full_document_draft_display': full_document_draft_display
        }
    }


def generate(state: RAG_State):
    print("---GENERATE---")
    # print(f"state: {state}")
    state_dict = state["keys"]
    question = state["original_query"]
    documents = state_dict.get("grading_results", {})
    document_title = state.get("document_title", "")
    full_documents_display = state_dict.get("full_document_draft_display", "")

    documents_for_prompt = ""
    if full_documents_display:
        save_document_to_md(full_document=full_documents_display, document_title=document_title)
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

    llm = get_anthropic_model(model_name="haiku")
    rag_chain = (generate_prompt.partial(additional_restrictions="9. ALWAYS USE 'PAR_Final_RespondSchema' Tool, so the user know your high-level-outline!\n10. Take a careful at the schema of the tool, and use the tool.")
                 | llm.with_structured_output(PAR_Final_RespondSchema))

    generation = rag_chain.invoke({
        "question": question,
        "documents": documents_for_prompt
    })

    return {
        "keys": {
            "generation": generation,
            "full_documents": documents_for_prompt
        }
    }

workflow = StateGraph(RAG_State)
# add node
workflow.add_node("multi_query_generator", multi_query_generator_node)
workflow.add_node("retrieve", retrieve_node)
workflow.add_node("grade_documents", grade_document)
workflow.add_node("think_high_level_outline", think_high_level_outline_node)
workflow.add_node("composable_search", composable_search_node)
workflow.add_node("generate", generate)

workflow.set_entry_point("multi_query_generator")

# add edge
workflow.add_edge("multi_query_generator", "retrieve")
workflow.add_edge("retrieve", "grade_documents")
# conditional edges
workflow.add_conditional_edges(
    "grade_documents",
    decide_to_generate,
    {
        "think_high_level_outline": "think_high_level_outline",
        "generate": "generate"
    }
)
workflow.add_edge("generate", END)
workflow.add_edge("think_high_level_outline", "composable_search")
workflow.add_edge("composable_search", "generate")
app = workflow.compile()

if __name__ == "__main__":
    print_warning_message()
    user_input = input("[y/n]:")

    if user_input == 'y':
        clear_console()
        user_query = input("What are you looking for?: ")
        inputs = {
            "original_query": user_query
        }

        result = app.invoke(inputs)
        print("####DOCUMENT####")
        print(result['keys']['full_documents'])
        print("----------------------------")

        final_result = result['keys']['generation']
        print(f"Final Result: {final_result.direct_response}\n"
              f"\n###BACKGROUND###\n{final_result.background}\n"
              f"###INTRODUCTION###\n{final_result.introduction}\n"
              f"###EXCERPTS###\n{final_result.excerpts}\n"
              f"###INSIGHTS###\n{final_result.insights}\n"
              f"###CONCLUSTION###\n{final_result.conclusion}\n"
              f"###ANY_HELPFUL###\n{final_result.any_helpful}\n")

    else:
        clear_console()
        print_see_you_again()

