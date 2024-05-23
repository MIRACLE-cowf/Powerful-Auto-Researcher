from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from CustomHelper.Helper import retry_with_delay_async
from CustomHelper.load_model import get_anthropic_model


async def conclusion_chain(
	previous_sections_info: str,
	conclusion_section_info: str
) -> str:
	llm = get_anthropic_model(model_name="haiku")
	fallback_llm = llm.with_fallbacks([llm] * 5)

	conclusion_prompt = ChatPromptTemplate.from_messages([
		("system", """You are an expert in writing conclusion sections for documents based on the information and insights obtained from other sections.
Your task is to write a comprehensive and insightful conclusion that effectively summarizes the key points, connects the main ideas, and provides a strong closing message for the given document, based on the information about the conclusion section and the previous sections.
And please writhe the conclusion section in Markdown format, starting with '## Conclusion' and using appropriate Markdown syntax for clarity and readability.

<previous_sections_info>
{previous_sections_info}
</previous_sections_info>

<instructions>
- Carefully review the provided information about the previous sections, including titles, key points, and main findings.
- Thoroughly examine the guidelines provided for the conclusion section.
- Identify common themes, patterns, and connections that emerge across multiple sections. Look for overarching concepts or ideas that tie the sections together.
- Summarize the most important points and takeaways from each section, focusing on the insights that are most relevant to the document's main topic or question.
- Synthesize the information from different sections to create a coherent and logical narrative. Show how the ideas from each section build upon or relate to one another.
- Highlight any significant conclusions, implications, or recommendations that can be drawn from the combined information presented in the document.
- If applicable, address any remaining questions, gaps, or areas for future exploration related to the document's main topic or question.
- Craft a strong and memorable closing statement that reinforces the main message or takeaway of the document. Ensure that the reader has a clear understanding of the document's significance and impact.
- Tailor the conclusion section guidelines based on the document's subject or field (e.g., technology, science, humanities) to address specific aspects or language styles relevant to the domain.
- Consider the document's purpose (e.g., persuasion, information sharing, problem-solving) and target audience (e.g., experts, general public) when crafting the conclusion section to ensure appropriate focus and tone.
- If necessary, provide guidance on collecting and utilizing additional information or resources to supplement the conclusion section and enhance its completeness.
</instructions>

<restrictions>
- Do not introduce new information or ideas that have not been discussed in the previous sections. The conclusion should be based solely on the content presented earlier in the document.
- Avoid simply repeating or summarizing the information from the previous sections without adding insights or drawing connections. The conclusion should offer a fresh perspective or synthesis of the material.
- Keep the conclusion concise and focused, avoiding unnecessary details or tangents. Aim for a length that is approximately 10-15% of the total document length.
- Use clear and persuasive language that is appropriate for the intended audience. Avoid jargon or technical terms that may confuse or alienate readers.
- Provide a sense of closure and completeness to the document while leaving the reader with something to think about or consider further.
- Use Markdown formatting elements such as headings, bullet points, and emphasis to structure the conclusion section and highlight key points.
</restrictions>


By following these guidelines and considering the information from both the previous sections and the provided conclusion section guidelines, please write a comprehensive and insightful conclusion section for the document.
"""),
		("human", "{input}")
	])

	_conclusion_chain = conclusion_prompt | fallback_llm | StrOutputParser()

	print('---ENTER CONCLUSION CHAIN---')
	conclusion = await retry_with_delay_async(
		chain=_conclusion_chain,
		input={
			"previous_sections_info": previous_sections_info,
			"input": conclusion_section_info
		},
		max_retries=3,
		delay_seconds=45.0,
	)
	return conclusion
