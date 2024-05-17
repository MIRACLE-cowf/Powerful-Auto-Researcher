import re

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from CustomHelper.load_model import get_anthropic_model


def _parse_generate_new_question_chain(
	generated_prompt: str
) -> str:
	generated_prompt_match = re.search(r"<generated_prompt>(.*?)</generated_prompt>", generated_prompt, re.DOTALL)
	if generated_prompt_match:
		return generated_prompt_match.group(1).strip()
	else:
		return generated_prompt


async def GenerateNewPromptFunc(
	user_input: str,
) -> str:
	llm = get_anthropic_model(model_name="opus")

	prompt = ChatPromptTemplate.from_messages([
		("system", """You will be assisting with a RAG (Retrieval-Augmented Generation) AI system that generates new search questions based on user questions. Your task is to take a user's question, translate it into English if needed, identify the key information sought, and generate a new prompt in English based on that key information.


	<instructions>
	1. Check if the question is already in English. If it is not, translate it into English. Output the translated question inside <translated_question> tags.

	2. analyze the question to determine the key information the user is seeking. Consider the main topic, specific details requested, and the desired output format if specified. Write the key information inside <key_info> tags.

	3. use the key information to generate a new questions in English. The question should be clear, concise, and structured to elicit the most relevant and accurate response from the AI system. Ensure that the prompt captures the core intent of the original question. Write the generated prompt inside <generated_prompt> tags.
	</instructions>

	<example>
	<user_question>
	What is the capital of France and can you provide a brief history of the city?
	</user_question>
	<key_info>
	- Capital of France
	- Brief history of the capital city
	</key_info>
	<generated_new_question>
	What is the capital city of France? Please provide a concise overview of the city's history, including notable events, landmarks, and cultural significance.
	</generated_new_question>
	</example>

	<restrictions>
	- Translate the question into English if needed, and output the translation in <translated_question> tags
	- Identify and output the key information in <key_info> tags
	- Generate and output the new prompt in English within <generated_prompt> tags
	</restrictions>
	Provide your output immediately, without any additional explanations or apologies.
	"""),
		("human", "<user_question>\n{input}\n</user_question>")
	])

	_generate_new_question_chain = prompt | llm | StrOutputParser()

	print(f'---ENTER CONVERT NEW QUESTION BY USER QUESTION: {user_input}')
	new_question = await _generate_new_question_chain.ainvoke({
		"input": user_input,
	})
	generated_new_prompt = _parse_generate_new_question_chain(new_question)
	return generated_new_prompt
