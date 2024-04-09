from typing import TypedDict, Dict

from langchain import hub
from langchain_text_splitters import CharacterTextSplitter
from langgraph.graph import StateGraph, END
from langchain_core.pydantic_v1 import BaseModel, Field
from Graph.AgentGraph import search_graph
from CustomHelper.Helper import generate_doc_result, generate_final_doc_results
from Tool.Respond_Agent_Section_Tool import FinalResponse_SectionAgent
from Util.PAR_Helper import extract_result
from Util.Retriever_setup import parent_retriever
from CustomHelper.load_model import get_anthropic_model
from Single_Chain.GradingDocumentsChain import grading_documents_chain
from Single_Chain.MultiQueryChain import multi_query_chain
from Single_Chain.Retrieve_Vector_DB import search_vector_store

from Graph.THLO_Graph import THLO_Graph
from Util.console_controller import clear_console, print_warning_message, print_see_you_again

generate_prompt = hub.pull("miracle/par_generation_prompt")


class PAR_Final_RespondSchema(BaseModel):
    background: str = Field(description="Write main background based on provided documents")
    introduction: str= Field(description="Write main introduction based on provided documents")
    excerpts: str = Field(description="Write some important excerpts from the provided documents")
    insights: str = Field(description="Write your thoughts and insights based on provided documents")
    direct_response: str = Field(description="Write your final direct response based on provided documents")
    conclusion: str = Field(description="Write your conclusion based on provided documents")
    any_helpful: str = Field(description="If there is any useful or helpful information that can help the user in the future based on the provided documents.")


class RAG_State(TypedDict):
    original_query: str
    derived_queries: list
    keys: Dict[str, any]


def multi_query_generator_node(state):
    print("---STATE: GENERATE QUERY IN---")
    original_query = state["original_query"]
    multi_query_result = multi_query_chain(model=get_anthropic_model()).invoke({"question": original_query})
    print("---STATE: GENERATE QUERY OUT---")
    return {
        "derived_queries": multi_query_result
    }


def retrieve_node(state):
    print("---STATE: RETRIEVE NODE IN---")
    multi_queries = state["derived_queries"]
    retrieve_result = search_vector_store(
        multi_query=multi_queries,
        retriever=parent_retriever
    )
    print("---STATE: RETRIEVE NODE OUT---")

    return {
        "keys": {
            "retrieve_result": retrieve_result
        }
    }


def grade_document(state):
    print("---STATE: GRADING DOCUMENTS IN---")
    state_dict = state["keys"]
    retrieve_result = state_dict["retrieve_result"]
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

        if grade == "yes":
            print(f"---{new_query} GRADE: DOCUMENT RELEVANT---")
            final_doc_results = ""
            final_doc_results += generate_final_doc_results(documents, index)
            index += 3
            grading_results[new_query] = final_doc_results
        else:
            print(f"---{new_query} GRADE: DOCUMENT NOT RELEVANT---")
            grading_results[new_query] = "needsearch"

    print("---STATE: GRADING DOCUMENTS OUT---")
    return {
        "keys": {
            "grading_results": grading_results
        }
    }


def decide_to_generate(state):
    print("---STATE: DECIDE to GENERATE IN---")
    state_dict = state["keys"]
    grading_results = state_dict["grading_results"]

    cnt = 0
    for index, (query, result) in enumerate(grading_results.items(), start=1):
        if result == "needsearch":
            cnt += 1

    # print(f"needsearch count: {cnt}")
    print("---STATE: DECIDE to GENERATE OUT---")

    if cnt > 0:
        return "think_high_level_outline"
    else:
        return "generate"


def think_high_level_outline_node(state):
    print('---STATE: THINK HIGH LEVEL OUTLINE NODE---')
    state_dict = state["keys"]
    grading_results = state_dict["grading_results"]
    original_query = state["original_query"]
    derived_queries = ""
    for query, _ in grading_results.items():
        derived_queries += query + "\n"

    print('---IN: HIGH_LEVEL_OUTLINE_GRAPH--')
    high_level_outline = THLO_Graph.invoke({
        "original_question": original_query,
        'derived_queries': derived_queries
    })
    print('---OUT: HIGH_LEVEL_OUTLINE_GRAPH--')

    print(high_level_outline)
    return {
        "keys": {
            'high_level_outline': high_level_outline["search_query_engine_plan"]
        }
    }


def composable_search_node(state):
    print('---STATE: COMPOSABLE SEARCH NODE---')
    state_dict = state["keys"]
    generation_result = state_dict["high_level_outline"]

    sections = generation_result.sections

    # For prompt input
    full_document_draft_prompt = ""
    # For User
    full_document_draft_display = ""


    print('---AGENT BATCH START---')
    search_graph_batch_input = [{'original_question': state['original_query'], 'section_plan': section, 'order': section.order} for section in sections]
    search_graph_batch_result = search_graph.batch(search_graph_batch_input, {'recursion_limit': 100})
    print('---AGENT BATCH END---')

    # We perform agent parallel, so we need reordering document's each sections.
    ordered_results = { search_graph_result['order']: search_graph_result for search_graph_result in search_graph_batch_result}

    for order in sorted(ordered_results.keys()):
        print(f'---ORDER: {order}---')
        search_graph_result = ordered_results[order]
        if "agent_outcome" in search_graph_result and hasattr(search_graph_result['agent_outcome'], "return_values") and "output" in search_graph_result["agent_outcome"].return_values:
            extract_agent_result = extract_result(search_graph_result["agent_outcome"].return_values["output"])
            if extract_agent_result is not None:
                document = extract_agent_result
            else:
                document = search_graph_result["agent_outcome"].return_values["output"]
        elif "final_respond" in search_graph_result:
            document = search_graph_result["final_respond"]
        else:
            print(f"Unexpected agent outcome format: {search_graph_result}")
            raise ValueError(f"Unexpected agent outcome format: {search_graph_result}")

        if isinstance(document, FinalResponse_SectionAgent):
            full_document_draft_display += f"{document.section_title}\n\n{document.section_content}\n\n\n####Researcher Opinion\n\n{document.section_thought}\n\n\n\n"
            full_document_draft_prompt += f"#####{document.section_title}#####\n\n{document.section_content}\n\n###Researcher Opinion###\n\n{document.section_thought}\n\n"
        elif isinstance(document, dict):
            section_title = document.get("section_title")
            section_content = document.get("section_content")
            section_thought = document.get("section_thought")
            full_document_draft_prompt += f"#####{section_title}#####\n\n{section_content}\n\n###RESEARCHER OPINION###\n\n{section_thought}\n\n"
            full_document_draft_display += f"{section_title}\n\n{section_content}\n\n\n####RESEARCHER OPINION\n\n{section_thought}\n\n\n\n"
        else:
            full_document_draft_display += document
            full_document_draft_prompt += document

    print('---GENERATE DOCUMENT DRAFT DONE---')

    return {
        'keys': {
            'full_document_draft': full_document_draft_prompt,
            'full_document_draft_display': full_document_draft_display
        }
    }


def generate(state):
    print("---GENERATE---")
    # print(f"state: {state}")
    state_dict = state["keys"]
    question = state["original_query"]
    documents = state_dict.get("grading_results", {})
    full_documents = state_dict.get("full_document_draft", "")
    full_documents_display = state_dict.get("full_document_draft_display", "")

    documents_for_prompt = ""
    if full_documents and full_documents_display:
        documents_for_prompt = full_documents

        print("#####DOCUMENT#####\n\n")
        print(full_documents_display)
        print("#####DOCUMENT#####\n\n")
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

    # print(f"documents_for_prompt: {documents_for_prompt}")


    llm = get_anthropic_model(model_name="haiku")
    rag_chain = generate_prompt | llm.with_structured_output(PAR_Final_RespondSchema)



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

