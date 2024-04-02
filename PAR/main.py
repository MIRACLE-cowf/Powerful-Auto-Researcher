import os
from typing import TypedDict, Dict

from dotenv import load_dotenv
from langchain import hub
from langchain_core.output_parsers import StrOutputParser
from langchain_text_splitters import CharacterTextSplitter
from langgraph.graph import StateGraph, END

from AgentGraph import search_graph
from CustomHelper.Helper import generate_doc_result, generate_final_doc_results
from CustomHelper.load_model import get_anthropic_model, get_openai_embedding_model, get_anthropic_model_tools_ver
from GradingDocumentsChain import grading_documents_chain
from MultiQueryChain import multi_query_chain
from SearchFunc import search_vector_store
from langchain_pinecone import PineconeVectorStore

from THGGraph import THG_part

embedding = get_openai_embedding_model(model_name="small")
pinecone_index_name = "knowledge"
vectorstore = PineconeVectorStore(index_name=pinecone_index_name, embedding=embedding)
generate_prompt = hub.pull("miracle/par_generate_prompt")


class RAG_State(TypedDict):
    original_query: str
    keys: Dict[str, any]


def multi_query_generator_node(state):
    print("---STATE: GENERATE QUERY IN---")
    original_query = state["original_query"]
    multi_query_result = multi_query_chain(model=get_anthropic_model()).invoke({"question": original_query})
    print("---STATE: GENERATE QUERY OUT---")
    return {
        "keys": {
            "multi_queries": multi_query_result
        }
    }


def retrieve_node(state):
    print("---STATE: RETRIEVE NODE IN---")
    state_dict = state["keys"]
    multi_queries = state_dict["multi_queries"]
    retrieve_result = search_vector_store(
        multi_query=multi_queries,
        vectorStore=vectorstore
    )
    print("---STATE: RETRIEVE NODE OUT---")

    if retrieve_result is None:
        retrieve_result = "Relevant Document isn't retrieve!"

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

    grading_chain = grading_documents_chain(model=get_anthropic_model_tools_ver())

    for new_query, documents in retrieve_result.items():
        doc_str = generate_doc_result(documents)

        grade_result = grading_chain.invoke({
            "question": new_query,
            "documents": doc_str
        })

        grade = grade_result["binary_score"]

        if grade == "yes":
            final_doc_results = ""
            final_doc_results += generate_final_doc_results(documents, index)
            index += 3
            grading_results[new_query] = final_doc_results
        else:
            grading_results[new_query] = "needsearch"

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

    print(f"needsearch count: {cnt}")
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
    high_level_outline = THG_part.invoke({
        "original_question": original_query,
        'derived_queries': derived_queries
    })
    print('---OUT: HIGH_LEVEL_OUTLINE_GRAPH--')

    print(high_level_outline)
    return {
        "keys": {
            'high_level_outline': high_level_outline['keys']['generation']
        }
    }


def composable_search_node(state):
    print('---STATE: COMPOSABLE SEARCH NODE---')
    state_dict = state["keys"]
    generation_result = state_dict["high_level_outline"]
    generation_str_list = []
    for searchResult in generation_result:
        generation_str_result = ""
        generation_str_result += f"""<section name="{searchResult.name}">"""
        for index, search_query_data in enumerate(searchResult.search_queries, start=1):
            search_query = search_query_data['search_query']
            search_engine = search_query_data['search_engine']
            generation_str_result += f"""<search_query_{index}>
    <search_query>{search_query}</search_query>
    <search_engine>{search_engine}</search_engine>
    </search_query_{index}"""
        generation_str_list.append(generation_str_result)

    full_document_draft = ""
    for index, generate_text in enumerate(generation_str_list, start=1):
        print(f'---GENERATE SECTION{index} DRAFT')
        mid_result = search_graph.invoke({'input': generate_text}, {'recursion_limit': 100})
        full_document_draft += mid_result['agent_outcome'].return_values['output'].lstrip("<final_document>").rstrip("</final_document>")

    print('---GENERATE DOCUMENT DRAFT DONE---')

    return {
        'keys': {
            'full_document_draft': full_document_draft
        }
    }


def generate(state):
    print("---GENERATE---")
    # print(f"state: {state}")
    state_dict = state["keys"]
    question = state["original_query"]
    documents = state_dict.get("grading_results", {})
    full_documents = state_dict.get("full_document_draft", "")

    documents_for_prompt = ""
    if full_documents:
        if "Try Again!" in full_documents:
            full_documents = full_documents.replace("Try Again!", "")
        documents_for_prompt = full_documents

        print("####DOCUMENT#####")
        print(documents_for_prompt)
        print("####DOCUMENT#####")
        user_response = input('[y/n] Would you want to save this document in Vector Store?: ')
        if user_response == 'y':
            text_splitter = CharacterTextSplitter(
                separator="\n\n",
                chunk_size=5000,
                chunk_overlap=500,
                length_function=len,
                is_separator_regex=False
            )
            texts = text_splitter.create_documents([documents_for_prompt])
            vectorstore.add_documents(texts)
            print("DOCUMENT SAVED AT VECTORSTORE SUCCESSFULLY!")
    else:
        for query, document in documents.items():
            documents_for_prompt += document

    # print(f"documents_for_prompt: {documents_for_prompt}")


    llm = get_anthropic_model(model_name="haiku").bind(stop=["</response>"])
    rag_chain = generate_prompt | llm | StrOutputParser()



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
    user_query = input("What are you looking for?: ")
    inputs = {
        "original_query": user_query
    }

    result = app.invoke(inputs)
    print("####DOCUMENT####")
    print(result['keys']['full_documents'])
    print("----------------------------")

    print(result["keys"]["generation"])