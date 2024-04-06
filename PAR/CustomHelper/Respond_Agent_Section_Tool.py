from typing import Type, Optional

from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.tools import BaseTool


class FinalResponse_SectionAgent(BaseModel):
    section_title: str = Field(description="Section Title. DO NOT tagging <section_title> tags")
    section_content: str = Field(description="section search results. DO NOT tagging <section_content> tags")
    section_thought: str = Field(description="your final thought about this section. DO NOT tagging <section_thought> tags")


class FinalResponseTool(BaseTool):
    name: str = 'Final-Respond'
    description: str = ("This tool is used to return sections search results to users."
                        "ALWAYS use it only when all the information about the section has been collected and you are ready to finally inform the user of all the information about the section."
                        "If you do not use this tool, you will not be able to forward the results to users, and so you will be penalized."
                        "If all the information has not been collected, please do not use it."
                        "DO NOT TAGGING <result> tags"
                        "The 'section_title' parameter is the title of the section."
                        "The 'section_content' parameter is the collection of the section and you can put all the things you can fill in the section."
                        "Lastly, the 'section_thought' parameter is your final thought of the section so user can know your think.")
    args_schema: Type[FinalResponse_SectionAgent] = FinalResponse_SectionAgent

    def _run(
            self,
            query: str,
            run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Use the Wikipedia tool."""
        return "X"