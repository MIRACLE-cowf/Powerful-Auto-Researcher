from typing import List, Any
from langchain_core.exceptions import OutputParserException
from langchain_core.output_parsers import BaseOutputParser
from langchain_core.outputs import Generation, ChatGeneration


# Will be deprecated
class AnthropicOutputParser(BaseOutputParser):
    @property
    def _type(self) -> str:
        return "json_functions"

    def parse(self, text: str) -> Any:
        raise NotImplementedError()

    def parse_result(self, result: List[Generation], *, partial: bool = False) -> Any:
        if len(result) != 1:
            raise OutputParserException(
                f"Expected exactly one result, but got {len(result)}"
            )
        generation = result[0]
        if not isinstance(generation, ChatGeneration):
            raise OutputParserException(
                "This output parser can only be used with a chat generation."
            )
        message = generation.message
        # print(f"message: {message}")

        if "<invoke>" in message.content:
            start_tag = "<invoke>"
            end_tag = "</invoke>"
            invoke_text = message.content[
                          message.content.find(start_tag) + len(start_tag):message.content.find(end_tag)
                          ]
            if "<tool_name>" in invoke_text:
                start_tag = "<tool_name>"
                end_tag = "</tool_name>"
                tool_name = invoke_text[invoke_text.find(start_tag) + len(start_tag):invoke_text.find(end_tag)]

                parameters = {}
                if "<parameters>" in invoke_text:
                    start_tag = "<parameters>"
                    end_tag = "</parameters>"
                    parameters_text = invoke_text[
                                      invoke_text.find(start_tag) + len(start_tag):invoke_text.find(end_tag)]
                    parameter_pairs = parameters_text.strip("\n").split(">")

                    current_key = None
                    current_value = ""
                    for pair in parameter_pairs:
                        pair = pair.lstrip("\n").rstrip("\n").strip("\n")
                        if pair == '':
                            continue
                        elif pair.startswith("<"):
                            if current_key:
                                parameters[current_key] = current_value.strip()
                            current_key = pair.lstrip("<").strip()
                            current_value = ""
                        else:
                            current_value += pair.removesuffix(f"</{current_key}")

                    if current_key:
                        parameters[current_key] = current_value.strip()
                    return parameters
        else:
            return message
