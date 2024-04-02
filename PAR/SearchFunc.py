from typing import List

from langchain_core.vectorstores import VectorStore


def search_vector_store(
        multi_query: List[str],
        vectorStore: VectorStore,
        k=3
):
    query_results = {}
    for query in multi_query:
        print("---RETRIEVING---")
        docs = vectorStore.similarity_search(query, k=k)
        query_results[query] = docs
    return query_results
