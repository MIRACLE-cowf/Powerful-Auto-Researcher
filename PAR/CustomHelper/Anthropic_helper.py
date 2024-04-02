from typing import Any, Dict
from langchain_anthropic.experimental import ChatAnthropicTools, _xml_to_tool_calls
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.outputs import ChatResult, ChatGeneration


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
