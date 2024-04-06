from typing import List
from langchain_core.pydantic_v1 import BaseModel, Field


# Anthropic supported calling tool! So we can use structured output to use langchain

class Thought(BaseModel):
    overall_thought: str = Field(description="Write my overall thought.")
    motivation: str = Field(description="My motivation.")
    desired_information: str = Field(description="My desired information.")
    gaps_or_limitations: str = Field(description="My gaps or limitations part.")
    document_structure: str = Field(description="My document structure part.")

    def as_str(self) -> str:
        return f"""<overall_thought>\n{self.overall_thought}\n</overall_thought>\n
<motivation>\n{self.motivation}\n</motivation>\n
<desired_information>\n{self.desired_information}\n</desired_information>\n
<gaps_or_limitations>\n{self.gaps_or_limitations}\n</gaps_or_limitations>\n
<document_structure>\n{self.document_structure}\n</document_structure>\n"""


class SectionContent(BaseModel):
    overview: str = Field(..., description="A brief overview of the section")
    key_points: List[str] = Field(..., description="The main points to be covered in the section")
    description: str = Field(..., description="Provide a description of the high-level plan for this overview")


class Section(BaseModel):
    name: str = Field(..., description="The name of the section")
    content: List[SectionContent] = Field(...,
                                          description="Provide a description of the high-level plan for this section's content")


class HighLevelDocument_Outline(BaseModel):
    title: str = Field(..., description="The title of the completed document")
    sections: List[Section] = Field(..., description="List the sections of the document.")

    def as_str(self) -> str:
        xml_output = f"<document>\n<title>{self.title}</title>\n"

        for section in self.sections:
            xml_output += f"<section>\n<name>{section.name}</name>\n"

            for content in section.content:
                xml_output += "<content>\n"
                xml_output += f"<overview>{content.overview}</overview>\n"

                xml_output += "<key_points>\n"
                for key_point in content.key_points:
                    xml_output += f"<key_point>{key_point}</key_point>\n"
                xml_output += "</key_points>\n"

                xml_output += f"<description>{content.description}</description>\n"
                xml_output += "</content>\n"

            xml_output += "</section>\n\n"

        xml_output += "</document>"
        return xml_output


class SearchModel(BaseModel):
    search_engine: List[str] = Field(..., description="Choose the search engine to search for this section.")
    search_query: List[str] = Field(...,
                                    description="Enter the search query to be used in the selected search engine for this section.")


class SectionPlan(BaseModel):
    title: str = Field(..., description="The name of the section")
    plan: List[SearchModel] = Field(..., description="Provide a high-level plan of this section")
    explanation: str = Field(..., description="The explanation of the section")

    def as_str(self) -> str:
        xml_output = f"<section>\n<title>{self.title}</title>\n"
        xml_output += f"<explanation>{self.explanation}</explanation>\n"
        for _plan in self.plan:
            xml_output += "<plan>\n<search_engines>\n"
            for search_engine in _plan.search_engine:
                xml_output += search_engine + "\n"
            xml_output += "</search_engines>\n"
            xml_output += "<search_queries>\n"
            for search_query in _plan.search_query:
                xml_output += search_query + "\n"
            xml_output += "</search_queries>\n"
            xml_output += "</plan>"

        xml_output += "</section>"
        return xml_output


class HighLevelDocument_Plan(BaseModel):
    title: str = Field(..., description="The title of the completed document")
    sections: List[SectionPlan] = Field(description="Provide a high-level plan of the each sections")

    def as_str(self) -> str:
        xml_output = f"<document>\n<title>{self.title}</title>\n"

        for section in self.sections:
            xml_output += f"<section>\n<title>{section.title}</title>\n"

            xml_output += "<plan>\n"
            for search_model in section.plan:
                xml_output += "<search_model>\n"
                xml_output += "<search_engines>\n"
                for engine in search_model.search_engine:
                    xml_output += f"<engine>{engine}</engine>\n"
                xml_output += "</search_engines>\n"
                xml_output += "<search_queries>\n"
                for query in search_model.search_query:
                    xml_output += f"<query>{query}</query>\n"
                xml_output += "</search_queries>\n"
                xml_output += "</search_model>\n"
            xml_output += "</plan>\n"

            xml_output += f"<explanation>{section.explanation}</explanation>\n"
            xml_output += "</section>\n"

        xml_output += "</document>"
        return xml_output
