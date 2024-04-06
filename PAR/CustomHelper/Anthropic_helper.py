from typing import Any, Dict, Sequence, Tuple, List
from langchain_anthropic.experimental import ChatAnthropicTools, _xml_to_tool_calls
from langchain_core.agents import AgentAction
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage, BaseMessage
from langchain_core.outputs import ChatResult, ChatGeneration

from CustomHelper.Custom_AnthropicAgentOutputParser import AnthropicAgentAction



# WE can use basically same as LangChain OpenAI's 'format_to_openai_tool_message', but little bit custom is there
def _create_tool_message(
    agent_action: AnthropicAgentAction, observation: str
) -> ToolMessage:
    """Convert agent action and observation into a function message.
    Args:
        agent_action: the tool invocation request from the agent
        observation: the result of the tool invocation
    Returns:
        FunctionMessage that corresponds to the original tool invocation
    """
    if not isinstance(observation, str):
        try:
            import json
            content = json.dumps(observation, ensure_ascii=False)
        except Exception:
            content = str(observation)
    else:
        content = observation
    return ToolMessage(
        tool_call_id=agent_action.tool_call_id,
        content=content,
        additional_kwargs={"name": agent_action.tool},
    )


def format_to_anthropic_tool_messages(
    intermediate_steps: Sequence[Tuple[AgentAction, str]],
) -> List[BaseMessage]:
    """Convert (AgentAction, tool output) tuples into FunctionMessages.

    Args:
        intermediate_steps: Steps the LLM has taken to date, along with observations

    Returns:
        list of messages to send to the LLM for the next prediction

    """
    messages = []
    for agent_action, observation in intermediate_steps:
        if isinstance(agent_action, AnthropicAgentAction):
            new_messages = list(agent_action.message_log) + [
                _create_tool_message(agent_action, observation)
            ]
            messages.extend([new for new in new_messages if new not in messages])
        else:
            messages.append(AIMessage(content=agent_action.log))
    return messages

def convert_intermediate_steps(intermediate_steps):
    """For Custom Anthropic Agent.
    Similar to LangChain's OpenAI Agent's convert_intermediate_steps function."""
    log = []
    for index, (action, observation) in enumerate(intermediate_steps):
        if index % 2 == 0:
            log.append(AIMessage(f"""Tool Result:
<function_results>
<result>
<tool_name>{action.tool}</tool_name>
<tool_input>{action.tool_input}</tool_input>
<stdout>{observation}</stdout>
</result>
</function_results>
What is next step? Use <function_calls> tags."""))
        else:
            log.append(HumanMessage(f"""Tool Result:
<function_results>
<result>
<tool_name>{action.tool}</tool_name>
<tool_input>{action.tool_input}</tool_input>
<stdout>{observation}</stdout>
</result>
</function_results>
What is next step? Use <function_calls> tags."""))
    return log


def convert_tools(tools: list):
    return "\n".join(
        [
            f"""Tool {index+1}:
Name: {tool.name}
Description: {tool.description}
Parameter: {tool.args}""" for index, tool in enumerate(tools)
        ]
    )


class CustomAnthropicTools(ChatAnthropicTools):
    def _format_output(self, data: Any, **kwargs: Any):
        try:
            text = data.content[0].text

            tools = kwargs.get("tools", None)

            additional_kwargs: Dict[str, Any] = {}

            if tools:
                # parse out the xml from the text
                try:
                    # get everything between <function_calls> and </function_calls>
                    start = text.find("<function_calls>")
                    end = text.find("</function_calls>") + len("</function_calls>")
                    xml_text = text[start:end]

                    xml = self._xmllib.fromstring(xml_text)
                    additional_kwargs["tool_calls"] = _xml_to_tool_calls(xml, tools)
                    text = ""
                except Exception:
                    pass

            return ChatResult(
                generations=[
                    ChatGeneration(
                        message=AIMessage(content=text, additional_kwargs=additional_kwargs)
                    )
                ],
                llm_output=data,
            )
        except Exception as e:
            return ChatResult(
                generations=[
                    ChatGeneration(
                        message=AIMessage(content="Try Again!")
                    )
                ],
            )
