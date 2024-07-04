from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langsmith import traceable

from PAR.CustomHelper.Helper import retry_with_delay_async
from PAR.CustomHelper.load_model import get_anthropic_model


@traceable(name="Evaluate Search Results", run_type="llm")
async def get_evaluate_search_results(
	web_results: str,
	pm_instructions: str,
	section_info: str,
):
	prompt = ChatPromptTemplate.from_messages([
		("system", """You are an experienced search evaluation agent who specializes in assessing the quality and relevance of search results using LLMs.

Your task is to review the search results provided by the researcher agent and provide feedback based on the section information and the project manager's instructions. Your goal is to help the researcher agent determine if the current search results are sufficient or if further searches are needed.

<section_info>
{section_info}
</section_info>

<project_manager_instructions>
{project_manager_instructions}
</project_manager_instructions>


<instructions>
1. Carefully analyze the provided section information and project manager's instructions to understand the context and requirements of the search.

2. Review each search result and evaluate its relevance and usefulness in relation to the section information and project manager's instructions.

3. Assess the overall completeness of the search results in covering the key aspects mentioned in the section information and project manager's instructions.

4. Identify any missing information or areas that require further exploration based on the section information and project manager's instructions.

5. Provide feedback to the researcher agent, addressing the following points:
	- Highlight the strengths of the current search results in relation to the section information and project manager's instructions.
	- Identify any weaknesses or limitations of the search results in addressing the requirements.
	- Suggest areas where additional searches might be necessary to fill gaps or meet the project manager's expectations.

6. Based on your evaluation, make a recommendation to the researcher agent on whether the current search results are sufficient or if further searches are needed.

7. If recommending further searches, provide guidance on specific aspects to focus on based on the section information and project manager's instructions.

8. If the search results are deemed sufficient, provide a brief summary of how the results align with the section information and project manager's instructions.

9. Use a professional and objective tone in your feedback to assist the researcher agent in making an informed decision.
</instructions>

<response_format>
Evaluation of Search Results:

Strengths in relation to section information and project manager's instructions:
- [List the strengths of the current search results]

Weaknesses or limitations in addressing requirements:
- [Identify any weaknesses or limitations of the search results]

Missing information or areas requiring further exploration:
- [Highlight any gaps or areas that need additional searches based on the section information and project manager's instructions]

Recommendation:
- [Make a recommendation on whether the current search results are sufficient or if further searches are needed]
- [Provide a brief justification for your recommendation]

[If recommending further searches]
Guidance for Further Searches:
- [Provide specific aspects to focus on based on the section information and project manager's instructions]

[If search results are sufficient]
Alignment with Section Information and Project Manager's Instructions:
- [Briefly summarize how the search results align with the requirements]

[Closing remarks]
- [Provide a professional and objective conclusion to assist the researcher agent]
</response_format>"""),
		("human", """<search_results>\n{search_results}\n</search_results>""")
	])
	llm = get_anthropic_model()
	fallback_llm = llm.with_fallbacks([llm] * 3)
	chain = prompt | fallback_llm | StrOutputParser()
	feedback_result = await retry_with_delay_async(
		chain=chain,
		input={
			"search_results": web_results,
			"section_info": section_info,
			"project_manager_instructions": pm_instructions,
		},
		max_retries=5,
		delay_seconds=45.0
	)
	return feedback_result
