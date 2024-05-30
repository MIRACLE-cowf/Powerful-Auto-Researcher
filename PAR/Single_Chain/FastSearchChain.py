from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableParallel
from langsmith import traceable

from CustomHelper.Helper import retry_with_delay_async
from CustomHelper.load_model import get_anthropic_model
from Tool.CustomBraveSearchFunc import _build_brave_results
from Tool.CustomSearchFunc_v2 import _get_content_extraction_agent
from Tool.CustomTavilySearchFunc import _build_raw_contents_tavily
from Tool.Custom_BraveSearchResults import get_brave_search_tool
from Tool.Custom_TavilySearchResults import get_tavily_search_tool


@traceable(name="Fast Search Func")
async def get_fast_search_result(
	original_question: str
) -> str:
	prompt = ChatPromptTemplate.from_template("""I'm going to give you a document. Then I'm going to ask you a question about it. I'd like you to first write down exact quotes from the document that would help answer the question, and then I'd like you to answer the question using facts from the quoted content.

Here is the document:
{document}


Here is the question: 
<question>
{question}
</question>

First, find the quotes from the document that are most relevant to answering the question, and list them in numbered order. Quotes should be relatively short.

If there are no relevant quotes, write "No relevant quotes" instead.

Then, answer the question, starting with "Answer:". Do not include or reference quoted content verbatim in the answer. Don't say "According to Quote [1]" when answering. Instead make references to quotes relevant to each section of the answer solely by adding their bracketed numbers at the end of relevant sentences.

Thus, the format of your overall response should look like what's shown between the <example> tags. Make sure to follow the formatting and spacing exactly.

<example>
<Relevant Quotes>
<Quote & URL>
Quote: [1] "Company X reported revenue of $12 million in 2021."
URL: https://www.example.com
</Quote & URL>
<Quote & URL>
Quote: [2] "Almost 90% of revenue came from widget sales, with gadget sales making up the remaining 10%."
URL: https://www.example2.com
</Quote & URL>
</Relevant Quotes>

<Answer>
[1] Company X earned $12 million. [2] Almost 90% of it was from widget sales.
</Answer>
</example>

If the question cannot be answered by the document, say so.
Answer the question immediately without preamble.""")

	llm = get_anthropic_model()
	fallback_llm = llm.with_fallbacks([llm] * 5)
	chain = prompt | fallback_llm | StrOutputParser()

	brave_search_tool_with_fallbacks = get_brave_search_tool(max_results=None)
	tavily_search_tool_with_fallbacks = get_tavily_search_tool(max_results=None)

	multiple_search_chain = RunnableParallel(brave=brave_search_tool_with_fallbacks, tavily=tavily_search_tool_with_fallbacks)
	multiple_search_results = multiple_search_chain.invoke({"query": original_question})

	web_results = {
		"brave": _build_brave_results(multiple_search_results['brave']),
		"tavily": _build_raw_contents_tavily(multiple_search_results['tavily']['results'])
	}

	_content_extraction_agent = _get_content_extraction_agent()
	batch_input = [
		{'search_query': original_question, 'search_result': web_results['brave']},
		{'search_query': original_question, 'search_result': web_results['tavily']},
	]

	extract_raw_contents_result = await retry_with_delay_async(
		chain=_content_extraction_agent,
		input=batch_input,
		max_retries=5,
		delay_seconds=45.0,
		is_batch=True
	)

	batch_results = _build_batch_results(extract_raw_contents_result)

	final_result = chain.invoke({"document": batch_results, "question": original_question})
	return final_result


def _build_batch_results(_extract_raw_contents_result: list):
	_batch_results = "<documents>\n"
	for index, batch in enumerate(_extract_raw_contents_result, start=1):
		_batch_results += (f"<document index={index}>\n"
		                  f"<extract_result>\n{batch}</extract_result>\n</document>\n\n")
	_batch_results += "</documents>\n"
	return _batch_results