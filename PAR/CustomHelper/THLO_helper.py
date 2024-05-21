from typing import List

from langchain_core.pydantic_v1 import BaseModel, Field


# Anthropic supported calling tool! So we can use structured output to use langchain
# 2024.04.10: Note: HighLevelDocument_Outline, HighLevelDocument_Plan's each parameter is added new feature and description is changed!
class Thought(BaseModel):
    """Use at THLO stage, thought chain, for structured output"""
    overall_thought: str = Field(description="Write my overall thought. Should be English")
    motivation: str = Field(description="My motivation. Should be English")
    desired_information: str = Field(description="My desired information. Should be English")
    gaps_or_limitations: str = Field(description="My gaps or limitations part. Should be English")
    document_structure: str = Field(description="My document structure part. Should be English")

    def as_str(self) -> str:
        return f"""<overall_thought>\n{self.overall_thought}\n</overall_thought>\n
<motivation>\n{self.motivation}\n</motivation>\n
<desired_information>\n{self.desired_information}\n</desired_information>\n
<gaps_or_limitations>\n{self.gaps_or_limitations}\n</gaps_or_limitations>\n
<document_structure>\n{self.document_structure}\n</document_structure>\n"""


class SectionContent(BaseModel):
    """Use at Section class"""
    overview: str = Field(..., description="A brief overview of the section. Should be English")
    key_points: List[str] = Field(..., description="The main points to be covered in the section. Should be English")
    description: str = Field(..., description="Provide a description of the high-level plan for this overview. Should be English")
    expected_outcome: str = Field(...,
                                  description="Describe the desired outcome or takeaway for the reader after completing this section. Should be English")
    relation_to_other_sections: str = Field(...,
                                            description="Explain how this section relates to or builds upon other sections in the document. Should be English")


class Section(BaseModel):
    """Use at HighLevelDocument_Outline class"""
    name: str = Field(..., description="The name of the section")
    content: List[SectionContent] = Field(...,
                                          description="Provide a description of the high-level plan for this section's content. Should be English")
    order: int = Field(..., description="Specify the position of this section in the document's overall structure. Should be English")
    importance: str = Field(..., description="Indicate the importance or priority of this section (high, medium, low). Should be English")


class HighLevelDocument_Outline(BaseModel):
    """To use structured output, always use this tool, so that the user can check it.
    title is 'string' type"""
    title: str = Field(..., description="The title of the completed document. Should be English")
    objective: str = Field(..., description="State the main objective or purpose of the document. Should be English")
    sections: List[Section] = Field(..., description="LIST-UP the sections of the document. Should be English")
    evaluation_criteria: str = Field(...,
                                     description="Define the criteria for evaluating the quality and effectiveness of the completed document. Should be English")

    def as_str(self) -> str:
        xml_output = f"<high_level_document_outline>\n"
        xml_output += f"<title>{self.title}</title>\n"
        xml_output += f"<objective>{self.objective}</objective>\n"

        xml_output += "<sections>\n"
        for section in self.sections:
            xml_output += f"<section>\n"
            xml_output += f"<name>{section.name}</name>\n"
            xml_output += f"<order>{section.order}</order>\n"
            xml_output += f"<importance>{section.importance}</importance>\n"

            xml_output += "<content>\n"
            for content in section.content:
                xml_output += "<item>\n"
                xml_output += f"<overview>{content.overview}</overview>\n"

                xml_output += "<key_points>\n"
                for key_point in content.key_points:
                    xml_output += f"<key_point>{key_point}</key_point>\n"
                xml_output += "</key_points>\n"

                xml_output += f"<description>{content.description}</description>\n"
                xml_output += f"<expected_outcome>{content.expected_outcome}</expected_outcome>\n"
                xml_output += f"<relation_to_other_sections>{content.relation_to_other_sections}</relation_to_other_sections>\n"
                xml_output += "</item>\n"
            xml_output += "</content>\n"

            xml_output += "</section>\n"
        xml_output += "</sections>\n"

        xml_output += f"<evaluation_criteria>{self.evaluation_criteria}</evaluation_criteria>\n"
        xml_output += "</high_level_document_outline>"

        return xml_output


class SearchModel(BaseModel):
    """Use at SectionPlan class"""
    search_engines: List[str] = Field(..., description="Choose the search engine to search for this section.. Should be English")
    search_queries: List[str] = Field(...,
                                    description="Enter the search query to be used in the selected search engine for this section.. Should be English")


class SectionPlan(BaseModel):
    """Use at HighLevelDocument_Plan class"""
    title: str = Field(..., description="The name of the section. Should be English")
    order: int = Field(..., description="Specify the position of this section in the document's overall structure. Should be English")
    explanation: str = Field(..., description="The explanation of the section. Should be English")
    content_type: str = Field(...,
                              description="Specify the type of content in this section (e.g., introduction, analysis, examples, conclusion). Should be English")
    synthesis_plan: str = Field(...,
                                description="Explain how the information from the search results will be synthesized and integrated into the section. Should be English")
    outline: str = Field(..., description="Provide a detailed outline of the section's structure and content flow. Should be English")

    key_points: List[str] = Field(..., description="List the key points to be covered in this section. Should be English")
    search_models: List[SearchModel] = Field(...,
                                             description="Provide search models for gathering information for this section. Should be English")

    def as_str(self) -> str:
        xml_output = f"<section>\n<title>{self.title}</title>\n"
        xml_output += f"<explanation>{self.explanation}</explanation>\n"
        xml_output += f"<content_type>{self.content_type}</content_type>\n"
        xml_output += "<key_points>\n"
        for point in self.key_points:
            xml_output += f"<point>{point}</point>\n"
        xml_output += "</key_points>\n"
        for search_model in self.search_models:
            xml_output += "<search_model>\n"
            xml_output += f"<search_engine>{search_model.search_engines}</search_engine>\n"
            xml_output += "<search_queries>\n"
            for query in search_model.search_queries:
                xml_output += f"<query>{query}</query>\n"
            xml_output += "</search_queries>\n"
            # xml_output += f"<expected_results>{search_model.expected_results}</expected_results>\n"
            # xml_output += f"<quality_reflection>{search_model.quality_reflection}</quality_reflection>\n"
            xml_output += "</search_model>\n"
        xml_output += f"<synthesis_plan>{self.synthesis_plan}</synthesis_plan>\n"
        xml_output += f"<outline>{self.outline}</outline>\n"
        xml_output += "</section>"
        return xml_output

    def as_str_for_basic_info(self) -> str:
        xml_output = f"<section>\n<title>{self.title}</title>\n"
        xml_output += f"<explanation>{self.explanation}</explanation>\n"
        xml_output += f"<content_type>{self.content_type}</content_type>\n"
        xml_output += "<key_points>\n"
        for point in self.key_points:
            xml_output += f"<point>{point}</point>\n"
        xml_output += "</key_points>\n"
        xml_output += f"<synthesis_plan>{self.synthesis_plan}</synthesis_plan>\n"
        xml_output += f"<outline>{self.outline}</outline>\n"
        xml_output += "</section>"
        return xml_output

    def as_str_title_explanation(self) -> str:
        return f"<section>\n<title>{self.title}</title>\n<explanation>{self.explanation}</explanation>\n</section>\n"


class HighLevelDocument_Plan(BaseModel):
    """To use structured output, always use this tool, so that the user can check it.
    title parameter is 'string' type, for the title of the completed document
    sections parameter is 'array' type, you must put section title, high-level plan of the section, explanation of the section."""
    title: str = Field(..., description="The title of the completed document. Should be English")
    objective: str = Field(..., description="State the main objective or purpose of the document. Should be English")
    sections: List[SectionPlan] = Field(..., description="Provide detailed plans for each section of the document. Should be English")

    def as_str(self) -> str:
        xml_output = f"<document>\n<title>{self.title}</title>\n"
        xml_output += f"<objective>{self.objective}</objective>\n"
        for section in self.sections:
            xml_output += section.as_str() + "\n"
        xml_output += "</document>"
        return xml_output
