from typing import Any

from langchain import hub
from langchain.retrievers.multi_query import LineListOutputParser
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableSerializable

prompt = hub.pull("miracle/par_multi_query_prompt_public")
output_parser = LineListOutputParser()


def multi_query_chain(model: ChatAnthropic) -> RunnableSerializable[Any, list[str]]:
    chain = (
        {
            "question": lambda x: x['question']
        }
        | prompt
        | model.bind(stop=["</answer>"])
        | output_parser
    )
    return chain