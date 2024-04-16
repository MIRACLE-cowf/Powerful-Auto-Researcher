from typing import List, Any
from langchain.agents import AgentOutputParser
from langchain_core.agents import AgentAction, AgentFinish, AgentActionMessageLog
from langchain_core.exceptions import OutputParserException
from langchain_core.messages import BaseMessage
from langchain_core.outputs import Generation, ChatGeneration


class AnthropicAgentAction(AgentActionMessageLog):
    tool_call_id: str
    assistant_message: BaseMessage


def is_tool_use(content):
    if isinstance(content, list):
        return any(item.get("type") == "tool_use" for item in content)
    elif isinstance(content, dict):
        return content.get("type") == "tool_use"
    else:
        return False


# We can use basically same as LangChain's 'OpenAIAgentOutputParser' but a little bit custom is there.
class AnthropicAgentOutputParser_beta(AgentOutputParser):
    @property
    def _type(self) -> str:
        return "json_functions"

    def parse(self, text: str) -> Any:
        # print(f"text: {text}")
        raise NotImplementedError()

    def parse_result(self, result: List[Generation], *, partial: bool = False) -> Any:
        # print(f"result: {result}")
        if len(result) != 1:
            raise OutputParserException(
                f"Expected exactly one result, but got {len(result)}"
            )
        generation = result[0]

        if not isinstance(generation, ChatGeneration):
            raise OutputParserException(
                "This output parser can only be used with a chat generation."
            )
        # print(f"AGENT OUTCOME: {generation.message.content}")
        if is_tool_use(generation.message.content):
            actions: List = []
            message_content = generation.message.content

            tool_content = None
            for content in message_content:
                if isinstance(content, dict) and 'id' in content and 'name' in content and 'input' in content:
                    tool_content = content
                    break

            if tool_content is not None:
                id = tool_content['id']
                tool_name = tool_content['name']
                tool_input = tool_content['input']

                content_msg = f"responded: {message_content}\n" if message_content else "\n"
                log = f"\nInvoking: `{tool_name} with `{tool_input} with tool_call_id: {id}`\n{content_msg}"

                actions.append(
                    AnthropicAgentAction(
                        tool=tool_name,
                        tool_input=tool_input,
                        log=log,
                        message_log=[generation.message],
                        tool_call_id=id,
                        assistant_message=generation.message
                    )
                )
            return actions

        else:
            content = generation.message.content
            return AgentFinish(
                return_values={"output": content}, log=str(content)
            )
