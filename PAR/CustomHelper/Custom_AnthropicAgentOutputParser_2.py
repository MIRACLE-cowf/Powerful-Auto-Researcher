import json
from typing import List, Union

from langchain.agents import AgentOutputParser
from langchain_core.agents import AgentActionMessageLog, AgentAction, AgentFinish
from langchain_core.exceptions import OutputParserException
from langchain_core.messages import BaseMessage, ToolCall
from langchain_core.output_parsers.base import T
from langchain_core.outputs import Generation, ChatGeneration


class AnthropicAgentAction(AgentActionMessageLog):
	tool_call_id: str


def parse_ai_message_to_tool_action(
	message: BaseMessage
):
	actions: List = []
	if message.tool_calls:
		tool_calls = message.tool_calls

	else:
		if not message.additional_kwargs.get("tool_calls"):
			return AgentFinish(
				return_values={"output": message.content}, log=str(message.content)
			)

		tool_calls = []
		for tool_call in message.additional_kwargs["tool_calls"]:
			function = tool_call["function"]
			function_name = function["name"]
			from json import JSONDecodeError
			try:
				args = json.loads(function["arguments"] or "{}")
				tool_calls.append(
					ToolCall(name=function_name, args=args, id=tool_call["id"])
				)
			except JSONDecodeError:
				raise OutputParserException(
					f"Could not parse tool input: {function} because "
					f"the `arguments` is not valid JSON."
				)
	for tool_call in tool_calls:
		function_name = tool_call["name"]
		_tool_input = tool_call["args"]
		if "__arg1" in _tool_input:
			tool_input = _tool_input["__arg1"]
		else:
			tool_input = _tool_input

		content_msg = f"responded: {message.content}\n" if message.content else "\n"
		log = f"\nInvoking: `{function_name}` with `{tool_input}`\n{content_msg}\n"
		actions.append(
			AnthropicAgentAction(
				tool=function_name,
				tool_input=tool_input,
				log=log,
				message_log=[message],
				tool_call_id=tool_call["id"],
			)
		)

	return actions


class AnthropicAgentOutputParser(AgentOutputParser):
	@property
	def _type(self) -> str:
		return "json_functions"

	def parse(self, text: str) -> Union[AgentAction, AgentFinish]:
		raise ValueError("Can only parse messages")

	def parse_result(self, result: List[Generation], *, partial: bool = False) -> T:
		if len(result) != 1:
			raise OutputParserException(
				f"Expected exactly one result, but got {len(result)}"
			)

		if not isinstance(result[0], ChatGeneration):
			raise ValueError("This output parser only works on ChatGeneration output")

		message = result[0].message
		# print(f'parsed message: {message}')
		return parse_ai_message_to_tool_action(message)