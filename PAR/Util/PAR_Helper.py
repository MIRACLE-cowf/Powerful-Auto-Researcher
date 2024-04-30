import os

from Tool.Respond_Agent_Section_Tool import FinalResponse_SectionAgent


def extract_result(text):
    """A function to extract output when Claude occasionally fails to use the provided tools for structured output.
    Args:
       text: The final response from the agent
    Returns:
       The extracted result for each tag
    """
    pattern_result = r'<result>(.*?)<\/result>'
    pattern_section_complete = r'<section_complete>(.*?)<\/section_complete>'
    pattern_section_title = r'<section_title>(.*?)<\/section_title>'
    pattern_section_content = r'<section_content>(.*?)<\/section_content>'
    pattern_section_thought = r'<section_thought>(.*?)<\/section_thought>'
    import re
    match_result = re.search(pattern_result, text, re.DOTALL)
    match_section_title = re.search(pattern_section_title, text, re.DOTALL)
    match_section_content = re.search(pattern_section_content, text, re.DOTALL)
    match_section_thought = re.search(pattern_section_thought, text, re.DOTALL)
    match_section_complete = re.search(pattern_section_complete, text, re.DOTALL)
    if match_result:
        if match_section_title and match_section_content and match_section_thought:
            return {
                "section_title": match_section_title.group(1).strip(),
                "section_content": match_section_content.group(1).strip(),
                "section_thought": match_section_thought.group(1).strip()
            }
        else:
            return match_result.group(1).strip()
    elif match_section_complete:
        if match_section_title and match_section_content and match_section_thought:
            return {
                "section_title": match_section_title.group(1).strip(),
                "section_content": match_section_content.group(1).strip(),
                "section_thought": match_section_thought.group(1).strip()
            }
        else:
            return match_section_complete.group(1).strip()
    elif match_section_title and match_section_content and match_section_thought:
        return {
            "section_title": match_section_title.group(1).strip(),
            "section_content": match_section_content.group(1).strip(),
            "section_thought": match_section_thought.group(1).strip()
        }
    else:
        return text


def parse_result_to_document_format(document: dict | FinalResponse_SectionAgent | str) -> str:
    """Returns the agent's response in different document formats based on the response type (dict, str, FinalResponse_SectionAgent)
    Args:
        document: The response generated by the agent, which can be one of dict, str, or FinalResponse_SectionAgent
    Return:
        If the document type is dict or FinalResponse_SectionAgent, extracts and returns as str
        If the document type is str, returns as is
    """
    if isinstance(document, FinalResponse_SectionAgent):
        return f"{document.section_title}\n\n{document.section_content}\n\n\n####Researcher Opinion\n\n{document.section_thought}\n\n\n\n"
    elif isinstance(document, dict):
        section_title = document.get("section_title")
        section_content = document.get("section_content")
        section_thought = document.get("section_thought")
        return f"{section_title}\n\n{section_content}\n\n\n####Researcher Opinion\n\n{section_thought}\n\n\n\n"
    else:
        return f"\n\n{document}"


def setup_new_document_format(document_title: str, document_description: str, original_question: str) -> str:
    """Process to set the document title for creating an MD file"""
    return f"# {document_title}\n\n## {original_question}\n\n{document_description}\n\n\n"


def save_document_to_md(full_document: str, document_title: str):
    """After confirming with the user whether to save the file, creates a markdown file with the document_title as the filename inside the src folder
    Args:
        full_document: The combined value of each agent's results generated through the parse_result_to_document_format function
        document_title: The document title generated by the LLM in the O stage of THLO
    Returns:
        None
    """
    print("#####DOCUMENT#####\n\n")
    print(full_document)
    print("#####DOCUMENT#####\n\n")

    user_response = input('[y/n] Would you want to save this document as a .md file?: ')
    if user_response.lower() == 'y':
        # create file name
        file_name = f"{document_title}.md"

        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        file_path = os.path.join(parent_dir, "src", file_name)

        with open(file_path, "w", encoding="utf-8") as file:
            file.write(full_document)

        print(f"DOCUMENT SAVED AS {file_name} SUCCESSFULLY")
    else:
        print("DOCUMENT NOT SAVED.")