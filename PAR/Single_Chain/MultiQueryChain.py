from langchain import hub
from langchain_core.pydantic_v1 import BaseModel, Field
from langsmith import traceable

from CustomHelper.Helper import retry_with_delay_async
from CustomHelper.load_model import get_anthropic_model


class DerivedQueries(BaseModel):
    derived_query_1: str = Field(description="Related search query 1 that focuses on a key aspect of the original question.")
    derived_query_2: str = Field(description="Related search query 2 that uses semantically similar phrases to the original question.")
    derived_query_3: str = Field(description="Related search query 3 that adds relevant context or expands on the potential intent behind the original question.")


@traceable(name="func(get_multi_query_for_retrieve)")
async def get_multi_query_for_retrieve(question: str):
    prompt = hub.pull("miracle/par_multi_query_prompt_public")
    llm = get_anthropic_model()
    chain = (
            {
                "question": lambda x: x['question']
            }
            | prompt
            | llm.with_structured_output(DerivedQueries)
    )
    _multi_query = await retry_with_delay_async(
        chain=chain,
        input={
            "question": question
        },
    )
    return _multi_query
