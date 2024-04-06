from langchain import hub
from langchain_anthropic.experimental import ChatAnthropic
from langchain_core.pydantic_v1 import BaseModel, Field

from CustomHelper.Custom_AnthropicOutputParser import AnthropicOutputParser


class grade(BaseModel):
    binary_score: str = Field(description="Relevance score 'yes' or 'no'")

def grading_documents_chain(
        model: ChatAnthropic
):

    grading_prompt = hub.pull("miracle/par_grading_documents_prompt_public")
    llm_with_tools = model.with_structured_output(grade)
    grading_chain = grading_prompt | llm_with_tools
    return grading_chain