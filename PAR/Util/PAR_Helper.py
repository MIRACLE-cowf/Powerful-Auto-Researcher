def extract_result(text):
    """We set Claude to output for structured. But sometimes Claude can't use the tool. So we need to extract ourself."""
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
        return None