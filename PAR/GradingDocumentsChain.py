from langchain import hub
from langchain_anthropic.experimental import ChatAnthropicTools
from langchain_core.pydantic_v1 import BaseModel, Field

from CustomHelper.Custom_AnthropicOutputParser import AnthropicOutputParser


def grading_documents_chain(
        model: ChatAnthropicTools
):
    class grade(BaseModel):
        binary_score: str = Field(description="Relevance score 'yes' or 'no'")

    grading_prompt = hub.pull("miracle/par_grading_documents_prompt_public")
    llm_with_tools = model.bind_tools(tools=[grade]).bind(stop=["</function_calls>"])
    grading_chain = grading_prompt | llm_with_tools | AnthropicOutputParser()
    return grading_chain