from typing import Any

from langchain import hub
from langchain_anthropic import ChatAnthropic
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.runnables import RunnableSerializable

prompt = hub.pull("miracle/par_multi_query_prompt_public")


class DerivedQueries(BaseModel):
    derived_query_1: str = Field(description="Related search query 1 that focuses on a key aspect of the original question.")
    derived_query_2: str = Field(description="Related search query 2 that uses semantically similar phrases to the original question.")
    derived_query_3: str = Field(description="Related search query 3 that adds relevant context or expands on the potential intent behind the original question.")


def multi_query_chain(model: ChatAnthropic) -> RunnableSerializable[Any, DerivedQueries]:
    chain = (
            {
                "question": lambda x: x['question']
            }
            | prompt
            | model.with_structured_output(DerivedQueries)
    )
    return chain
