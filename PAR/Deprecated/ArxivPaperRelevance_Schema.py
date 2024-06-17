from typing import Optional

from langchain_core.pydantic_v1 import BaseModel, Field


class ArxivPaperRelevance(BaseModel):
    """ALWAYS USE after ArxivPaper review it, 'is_relevance' parameter's type is 'string' put 'yes' or 'no'.
    extract_content parameter also needed"""
    is_relevance: str = Field(..., description="Whether the paper is relevant to the section. 'yes' or 'no'")
    title: Optional[str] = Field(default="", description="If the paper is relevant, provide the title of the arXiv paper")
    methods: Optional[str] = Field(default="", description="If the paper is relevant, provide a brief description of the methods used in the paper")
    key_findings: Optional[str] = Field(default="", description="If the paper is relevant, provide the main results or conclusions of the paper")
    significance: Optional[str] = Field(default="", description="If the paper is relevant, provide the importance or implications of the research")
    summary: Optional[str] = Field(default="", description="If the papaer is relevant, provide a concise summary of the paper's content")
    reason: Optional[str] = Field(default="",description="If the paper is not relevant, provide brief explanation of why.")

    def as_str(self) -> str:
        if self.is_relevance == "yes":
            output = ""
            output += f"<Title>\n{self.title}\n</Title>\n"
            output += f"<Methods>\n{self.methods}\n</Methods>\n"
            output += f"<KeyFindings>\n{self.key_findings}\n</KeyFindings>\n"
            output += f"<Significance>\n{self.significance}\n</Significance>"
            output += f"<Summary>\n{self.summary}\n</Summary>\n"
            return output
        else:
            return f"This is not relevant because {self.reason}"