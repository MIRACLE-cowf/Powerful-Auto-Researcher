from langchain_core.retrievers import BaseRetriever
from langsmith import traceable

from Single_Chain.MultiQueryChain import DerivedQueries


@traceable(name="Retrieve Vector DB", run_type="retriever")
def search_vector_store(
    multi_query: DerivedQueries,
    retriever: BaseRetriever,
    k=3
):
    query_results = {}
    print(f"---RETRIEVING QUERY: {multi_query}---")
    _batch_inputs = prepare_batch_input_data(multi_query)
    _batch_results = retriever.batch(_batch_inputs)

    query_results[multi_query.derived_query_1] = _batch_results[0]
    query_results[multi_query.derived_query_2] = _batch_results[1]
    query_results[multi_query.derived_query_3] = _batch_results[2]

    return query_results


def prepare_batch_input_data(multi_query: DerivedQueries) -> list:
    return [
        multi_query.derived_query_1,
        multi_query.derived_query_2,
        multi_query.derived_query_3,
    ]
