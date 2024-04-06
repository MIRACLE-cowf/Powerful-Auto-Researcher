from langchain_core.messages import AIMessage, HumanMessage


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