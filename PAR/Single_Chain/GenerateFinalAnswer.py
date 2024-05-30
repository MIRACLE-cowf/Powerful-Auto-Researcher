from langchain import hub
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableSerializable

from CustomHelper.load_model import get_anthropic_model

generate_prompt = hub.pull("miracle/par_generation_prompt")


def get_generate_final_answer_chain() -> RunnableSerializable:
	llm = get_anthropic_model(model_name="sonnet")
	fallback_llm = llm.with_fallbacks([llm] * 5)

	chain = (
			generate_prompt.partial(additional_restrictions="")
			| llm
			| StrOutputParser()
	)

	return chain
