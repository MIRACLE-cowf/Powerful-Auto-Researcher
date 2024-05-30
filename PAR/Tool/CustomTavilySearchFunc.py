import asyncio
from typing import Optional, Union, Literal

import requests
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from langsmith import traceable

from CustomHelper.Custom_Error_Handler import PAR_ERROR, PAR_SUCCESS
from CustomHelper.Helper import retry_with_delay_async
from CustomHelper.load_model import get_anthropic_model
from Tool.CustomSearchFunc_v2 import _get_content_extraction_agent
from Tool.Custom_TavilySearchResults import get_tavily_search_tool


def _get_proposal_visualization_chain():
	prompt = ChatPromptTemplate.from_messages([
		("system", """You are a data visualization specialized agent with extensive experience in creating effective visual representations of information.

Currently, you are a team member of the PAR project, working on enhancing the visual elements of a markdown document. Other agents have collected and extracted relevant information from various sources.

Your role is to analyze the extracted information and identify opportunities for creating visualizations that can effectively convey key insights and support the overall narrative of the document.

<instructions>
1. Carefully review the extracted information provided by other agents.
   - Understand the main concepts, entities, relationships, and trends present in the information.
   - Consider the context and purpose of the section where the visualizations will be used.

2. Identify data points, statistics, comparisons, or complex ideas that could benefit from visual representation.
   - Look for numerical data, percentages, or metrics that can be presented through charts or graphs.
   - Identify relationships, hierarchies, or connections between entities that can be illustrated using diagrams or networks.
   - Spot processes, flows, or sequences that can be visualized using flowcharts or timelines.
   - Consider concepts or categories that can be effectively displayed using tree structures, Venn diagrams, or other visual formats.

3. Determine the most appropriate type of visualization for each identified opportunity.
   - Select chart types (e.g., bar charts, line graphs, pie charts) that best suit the nature of the data and the message you want to convey.
   - Choose diagram styles (e.g., flow diagrams, mind maps, organizational charts) that effectively represent relationships or structures.
   - Consider using infographics, icons, or illustrations to present complex ideas or narratives in an engaging way.

4. Provide clear instructions for creating each proposed visualization.
   - Specify the data or information to be included in the visualization.
   - Describe the desired layout, structure, or composition of the visualization.
   - Suggest colors, styles, or visual elements that can enhance the clarity and aesthetic appeal of the visualization.
   - Offer any additional context or annotations that should accompany the visualization to aid understanding.

5. Ensure that the proposed visualizations align with the overall goals and narrative of the document.
   - Consider how each visualization contributes to the main message or argument being presented.
   - Ensure that the visualizations complement the surrounding text and do not distract from the flow of information.
   - Maintain consistency in visual styles and formatting throughout the document.
</instructions>

<response_format>
When proposing visualizations, please use the following format:

Visualization Proposal:
Related Extract: [Specify which extracted information the visualization relates to]
Visualization Type: [Specify the type of visualization, such as chart, diagram, infographic, etc.]
Data/Information to Include: [List the specific data points or information to be visualized]
Layout/Structure: [Describe the desired layout, structure, or composition of the visualization]
Visual Style Suggestions: [Suggest colors, styles, or visual elements to enhance the visualization]
Additional Context/Annotations: [Provide any additional context or annotations to accompany the visualization]
</response_format>

<restrictions>
- Propose ONLY ONE 'Visualization Proposal'
</restrictions>

As a data visualization specialized agent, analyze the extracted information and propose effective visualizations that can enhance the clarity, engagement, and persuasiveness of the PAR project document. Follow the guidelines and format specified above to create compelling visual elements that support the overall narrative.
"""),
		("human", "{extracted_data}")
	])
	llm = get_anthropic_model(model_name="sonnet")
	chain = prompt | llm | StrOutputParser()
	return chain


def _get_visualization_code_chain():
	class visualization_response(BaseModel):
		"""Use visualization_response tool for generate visualization"""
		type: Literal["markdown", "mermaid", "matplotlib"] = Field(description="visualization code syntax type")
		code: str = Field(description="visualization code, do not include backtick(`)")
		explanation: str = Field(description="visualization explanation")

	prompt = ChatPromptTemplate.from_messages([
		("system", """You are a data visualization specialist tasked with creating visual elements based on the visualization proposals provided by the PAR project team.

Your role is to transform the proposed visualizations into actual visual representations using Mermaid syntax for charts, diagrams, and other visualizations, and Markdown syntax for tables.

<instructions>
1. Review each visualization proposal carefully.
   - Understand the type of visualization requested (e.g., chart, diagram, table, etc.).
   - Identify the specific data points or information to be included in the visualization.
   - Consider the suggested layout, structure, and visual style for each visualization.

2. Create the visualizations using the appropriate syntax or code:
   a. For diagrams and flowcharts, use Mermaid syntax.
      - Familiarize yourself with the Mermaid syntax for creating different types of diagrams (e.g., flow charts, sequence diagrams, class diagrams).
      - Translate the proposed layout and structure into Mermaid code.
      - Use double quotes (") to enclose node names and labels in Mermaid syntax for clarity and consistency.
      - Incorporate any additional annotations or styling suggestions provided in the proposal.

   b. For tables, use Markdown syntax.
      - Organize the data into a tabular format using Markdown syntax for tables.
      - Ensure that the table headers and cell contents are properly aligned and formatted.
      - Apply any specified styling or formatting options to enhance the table's readability.

   c. For charts and other visualizations, use Python code.
      - Utilize appropriate Python libraries such as Matplotlib, Seaborn, or Plotly for creating charts and graphs.
      - Write Python code to generate the desired chart type (e.g., bar chart, line graph, pie chart) based on the provided data.
      - Customize the chart's appearance, labels, colors, and other visual elements according to the proposal's suggestions.


3. Provide the resulting visualization code along with any necessary explanations or instructions.
   - Include the Mermaid code for charts, diagrams, and other visualizations, and the Markdown table for tabular data.
   - Add comments or explanations to clarify any complex or custom aspects of the visualization code.
   - Specify any dependencies or requirements needed to render the visualizations correctly (e.g., Mermaid version).

4. Ensure that the generated visualizations align with the overall style and formatting of the PAR project document.
   - Maintain consistency in colors, fonts, and visual elements across all visualizations.
   - Test the rendering of the visualizations to ensure they display correctly within the document format.

5. Collaborate with the PAR project team to refine and iterate on the visualizations as needed.
   - Be open to feedback and suggestions from the team regarding the generated visualizations.
   - Make necessary adjustments or improvements based on the team's input to achieve the desired visual impact and clarity.
</instructions>

<restrictions>
- Use 'visualization_response' tool for generate response.
- Do not include backtick(`) in code part.
</restrictions>

As a data visualization specialist, your goal is to transform the proposed visualizations into actual visual elements using Mermaid syntax for charts, diagrams, and other visualizations, and Markdown syntax for tables. Follow the guidelines and format specified above to create clear, informative, and visually appealing visualizations that enhance the PAR project document.
"""),
		("human", "{visualization_proposal}")
	])
	llm = get_anthropic_model(model_name="sonnet")
	chain = prompt | llm.with_structured_output(visualization_response)
	return chain


def _is_pdf(url: str) -> bool:
	if not url:
		return False
	if url.lower().endswith(".pdf"):
		return True

	try:
		response = requests.get(url)
		response.raise_for_status()
		return 'application/pdf' in response.headers.get('Content-Type', '')
	except Exception as e:
		return False


def _build_tavily_results(search_results: dict) -> str:
	web_results = ""
	if isinstance(search_results.get("answer", ""), str):
		web_results = f"<overall_summary>\n{search_results['answer']}\n</overall_summary>\n\n"

	if isinstance(search_results.get("follow_up_questions", []), list) and len(search_results.get("follow_up_questions", [])) > 0:
		web_results += f"<recommended_follow_up_questions>\n"
		for index, follow_up_question in enumerate(search_results["follow_up_questions"], start=1):
			web_results += f"{index}. {follow_up_question}\n"
		web_results += "</recommended_follow_up_questions>\n"

	if isinstance(search_results.get("images", []), list) and search_results.get("images"):
		print(f"<tavily_has_images>\n{search_results['images']}\n</tavily_has_images>")

	return web_results


def _build_raw_contents_tavily(docs: list) -> str:
	if docs is None:
		return ""  # docs가 None인 경우 빈 문자열 반환

	raw_contents = ""
	for index, doc in enumerate(docs, start=1):

		if _is_pdf(doc['url']):
			continue

		raw_contents += (f"<document index='{index}'>\n"
		                 "<document_content_snippet>\n"
		                 f"{doc['content']}"
		                 "</document_content_snippet>\n"
		                 "<document_raw_content>\n"
		                 f"{doc['raw_content']}\n"
		                 "</document_raw_content>\n"
		                 f"<source>{doc['url']}</source>\n"
		                 "</document>\n\n")

	return raw_contents


@traceable(name="Tavily Search", run_type="tool")
async def tavily_search_func(
	query: str,
	max_results: Optional[int] = None,
) -> Union[PAR_SUCCESS, PAR_ERROR]:
	print(f"---SEARCHING IN WEB(Using TAVILY API): {query}---")

	tavily_search_tool_with_fallbacks = get_tavily_search_tool(max_results=max_results)

	try:
		search_results = await tavily_search_tool_with_fallbacks.ainvoke({"query": query + "."})

		if not isinstance(search_results, dict) and "results" in search_results:
			error_message = str(search_results) if isinstance(search_results, str) else "Unexpected error occurred!"
			print(f"---TAVILY SEARCH ERROR: standard: {error_message}---")
			return PAR_ERROR(error_message)

		docs = search_results["results"]
		web_results = _build_tavily_results(search_results)
		raw_contents = _build_raw_contents_tavily(docs)
		_content_extraction_agent = _get_content_extraction_agent()
		extract_raw_contents_result = await retry_with_delay_async(
			chain=_content_extraction_agent,
			input={
				"search_query": query,
				"search_result": raw_contents,
			},
			max_retries=5,
			delay_seconds=45.0
		)
		# extract_raw_contents_result = await _content_extraction_agent.ainvoke({"search_query": query, "search_result": raw_contents})
		web_results += f"\n\n<raw_content_extract>\n{extract_raw_contents_result}\n</raw_content_extract>\n\n"
		print("---TAVILY SEARCH DONE---")

		# _visualization_chain = _get_proposal_visualization_chain()
		# visualization_result = _visualization_chain.invoke({
		# 	"extracted_data": web_results
		# })
		# print(visualization_result)
		# return PAR_SUCCESS(visualization_result)
		# web_results = visualization_result + "\n\n" + "<data>" + web_results + "</data>\n"
		return PAR_SUCCESS(web_results)
	except Exception as e:
		print(f"---TAVILY SEARCH ERROR: {e}---")
		return PAR_ERROR(str(e))


if __name__ == "__main__":
	result = asyncio.run(tavily_search_func(
		query="GDP rankings by country",
		max_results=3,
	))

	visualization_code_chain = _get_visualization_code_chain()
	visualization_code_result = visualization_code_chain.invoke({
		"visualization_proposal": result.result
	})
	print(visualization_code_result.type)
	print(visualization_code_result.code)
	print(visualization_code_result.explanation)