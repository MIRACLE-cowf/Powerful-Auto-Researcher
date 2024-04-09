from typing import Type, Optional

from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.tools import BaseTool


#Each parameter's description is changed!
class FinalResponse_SectionAgent(BaseModel):
    section_title: str = Field(description="Title of the section. Start with '##' markdown syntax.")
    section_content: str = Field(description="Coherent and well-structured content for the section, integrating information from various sources, in Markdown format. If any subtitle is here start with '###' markdown syntax.")
    section_thought: str = Field(description="Your thoughts, insights and opinion on the section content.")


class FinalResponseTool(BaseTool):
    name: str = 'section_complete'
    description: str = ("This tool is used to return the final results of a section to the user."
                        "ONLY use this tool when:"
                        "1. All relevant information for the section has been collected from various sources like Google, arXiv, YouTube, and Wikipedia."
                        "2. The collected information has been properly organized and summarized according to the schema."
                        "3. The 'section_content' parameter has been written in a coherent and contextually natural way based on the collected information in Markdown format."
                        "4. Your thoughts and some powerful insights on the section content are well reflected in the 'section_thought' parameter."
                        "Use this tool ONLY when all of the above conditions are met, and you are ready to provide the user with a comprehensive, high-quality result for the section."
                        "DO NOT use this tool before all information gathering and organization is complete, as you will not be able to deliver the results to the user without using this tool."
                        "When using the tool, make sure to:"
                        "- Enter the exact title of the section in the 'section_title' parameter"
                        "- Provide the information collected from each source in the form of a list, organized according to the respective schemas."
                        "- Write the 'section_content' parameter based on the collected information, ensuring that it is grammatically correct, easy to read, and smoothly integrates information from different sources in Markdown format."
                        "- Present your thoughts, insights, and opinions on the section content in the 'section_thought' parameter to help the user understand that you reasoning process and gain additional context."
                        "Use this tool appropriately to provide the user with comprehensive, high-quality section results.")
    args_schema: Type[FinalResponse_SectionAgent] = FinalResponse_SectionAgent

    def _run(
            self,
            query: str,
            run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Do Nothing!"""
        return "X"