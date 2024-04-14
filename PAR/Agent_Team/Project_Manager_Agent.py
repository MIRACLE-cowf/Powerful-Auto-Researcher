import operator
from typing import Literal, TypedDict, Annotated, Union

from langchain_anthropic.output_parsers import ToolsOutputParser
from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.pydantic_v1 import BaseModel, Field
from langgraph.graph import StateGraph, END

from Agent_Team.Member.PAR_ArXiv_Search_Agent_Graph import PAR_Team_Member_Agent_ArXiv
from Agent_Team.Member.PAR_Document_Writer import Document_Writer_chain
from Agent_Team.Member.PAR_Tavily_Search_Agent_Graph import PAR_Team_Member_Agent_Tavily
from Agent_Team.Member.PAR_Wikipedia_Search_Agent_Graph import PAR_Team_Member_Agent_Wikipedia
from Agent_Team.Member.PAR_Youtube_Search_Agent_Graph import PAR_Team_Member_Agent_Youtube
from CustomHelper.Anthropic_helper import format_to_anthropic_tool_messages
from CustomHelper.Custom_AnthropicAgentOutputParser import AnthropicAgentOutputParser_beta
from CustomHelper.load_model import get_anthropic_model
from Util.PAR_Helper import extract_result

members = ["tavily_agent", "document_agent", "wikipedia_agent", "youtube_agent", "arxiv_agent"]


class route(BaseModel):
    """Select the next agent.
    Remember the next agent can't access provided section. So you MUST provide specific and clear instructions to next agent."""
    next: Literal["tavily_agent", "document_agent", "wikipedia_agent", "youtube_agent", "arxiv_agent", "FINISH"] = Field(...,
                                                                      description="Select the next agent")
    instructions: str = Field(..., description="Provide specific and clear instructions that next agent what should do.")


PM_Prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a highly experienced and perfect Project Manager Agent who has worked in this role for a long time.

You are now in charge of a project called "PAR" to write a specific section of an entire MarkDown document. Other sections will be handled by different Project Manager Agents.

Your team consists of agents specialized in different search engines and an agent dedicated to document generation.

Your role is to effectively coordinate and collaborate with your team memebers to create a perfect section of the document when provided with overall guidelines and content for the specific section.

<instructions>
1. Analyze the given section information thoroughly to identify the necessary search engines and search queries.
2. Send search requests to each search agent and collect the results.
3. When evaluating the collected search results, rigorously assess the elements within the <search_evaluation></search_evaluation> XML tag.
- Relevance to the section topic
- Quality and reliability of the information
- Comprehensiveness and diversity of the content
- Usefulness for document creation
4. Only accept search results that meet a certain threshold in the evaluation.
5. If the search results are deemed insufficient, identify areas that require additional search and re-request the agent who conducted the initial search.
6. Apply steps 1-5 to the necessary search agents.
7. When you determine that sufficient high-quality information has been collected to generate the section, call upon the agent specializing in document generation.
8. Provide the document generation agent with the information and guidlines specificed in the <document_writing_guidlines></document_writing_guidlines> XML tag.
- Section title and description
- Key content and keywords to be covered in the section
- Search results and sources to refer to
- Document objective and reader's purpose
- Guidelines for document tone and style
- Desired document structure and length
9. Review the output from the document generation agent and request revisions if necessary.
10. Once the final document is complete, deliver it to the user.
11. When providing instructions to the agents, keep in mind that the selected agents do not have access to the section content. Therefore, provide specific and clear instructions to the selected agents.
</instructions>

<restrictions>
1. Exclude sources that are unreliable or low in quality.
2. Be mindful not to exceed the allocated time and resources for search and document creation.
3. Do not cover content beyond the scope of the given section.
4. Thoroughly review the generated document for any errors or inappropriate content.
5. Maintain smooth and respectful interactions among agents.
</restrictions>


<serach_evaluation>
1. Relevance to the section topic
- Evaluate whether the search result is directly related to the section's title, description, and key content.
- Assess the degree of relevance on a scale of 1 (very low) to 5 (very high).
- Only accept search results with a relevance score of 3 or higher.
2. Quality and reliability of the information
- Verify if the source of the search result is a reputable institution, expert, or academic material.
- Check the recency of the information and exclude outdated or non-updated content.
- Evaluate the accuracy and objectivity of the information, discarding subjective or biased content.
3. Comprehensiveness and diversity of the content
- Assess whether the search result covers the section topic from various perspectives.
- Ensure that the key content to be covered in the section is comprehensively included.
- Check if various examples, cases, and data are included.
4. Usefulness for document creation
- Determine if the search result contains information that is practically helpful for writing the section.
- Consider whether the content can support the explanation, flow, and argumentation of the section.
- Evaluate if the information from the search result can enhance readability and comprehension when utilized in the document.
</search_evaluation>



<document_writing_guidelines>
1. Section title and description
- Clearly understand the given section title and description, and write the document based on them.
- Faithfully reflect the content specified in the title and description, adding supplementary explanations if necessary.
2. Key content and keywords
- Identify the key content and keywords that must be covered in the section and appropriately incorporate them into the document.
- Structure the document around the key content and utilize keywords to emphasize important concepts and topics.
3. Reference search results and sources
- Actively utilize the provided search results and sources to write the document.
- Clearly cite the sources when quoting or referencing information from the search results, adhering to copyright guidelines.
- Rather than directly copying the search results, understand the content and reconstruct it in your own words.
4. Document tone and style
- Consistently write the document in accordance with the markdown style guide.
- Maintain a professional and objective tone while keeping it approachable for the reader.
- Focus on providing information and explanations that align with the document's objectives and help the reader's understanding.
- Using emojis to avoid a rigid atmosphere of section.
5. Document structure and length
- Follow the suggested document structure while considering the logical flow and connectivity of the content.
- Adhere to the length guidelines but prioritize the thoroughness and completeness of the content.
- If necessary, divide the section into subsections to deliver information systematically.
</document_writing_guidelines>

As the Project Manager Agent, strive to coordinate your team members effectively based on the above guidelines and constraints to create a high-quality section of the document."""),
    ("human", "<provided_section>\n{input}\n</provided_section>"),
    MessagesPlaceholder(variable_name="agent_scratchpad")
])

PM_llm = get_anthropic_model(model_name="sonnet")
PM_output_parser = ToolsOutputParser()


def extract_output(output):
    print(f"output: {output}")
    agent_output = output
    if isinstance(agent_output, list) and len(agent_output) > 0:
        return {
            "agent_output": agent_output[0],
            "next": agent_output[0].tool_input["next"],
            "instructions": agent_output[0].tool_input["instructions"],
        }
    else:
        return {
            "agent_output": agent_output,
            "next": "FINISH"
        }


PM_chain = (
    {
        "input": lambda x: x["input"],
        "agent_scratchpad": lambda x: format_to_anthropic_tool_messages(x["intermediate_steps"])
    }
    | PM_Prompt
    | PM_llm.bind_tools(tools=[route])
    | AnthropicAgentOutputParser_beta()
    | extract_output
)


class AgentState(TypedDict):
    order: int
    input: str
    agent_output: Union[AgentAction, AgentFinish, None]
    intermediate_steps: Annotated[list[tuple[AgentAction, str]], operator.add]
    next: str
    instructions: str
    search_result: str


def transform_search_result(search_engine: str, search_result: str) -> str:
    return f"<{search_engine}_search_result>\n\n{search_result}\n\n</{search_engine}_search_result>"


# def PM_agent_node(state):
#     print(f"PM_agent_node: {state}")
#     PM_result = PM_chain.invoke(state)

def tavily_agent_node(state):
    print(f"tavily_agent_node: {state}")
    messages = HumanMessage(content=f"Hi! I'm PAR Project Manager Agent! {state['instructions']}")
    tavily_agent_result = PAR_Team_Member_Agent_Tavily.invoke({"input": messages.content})
    extract_tavily_agent_result = extract_result(tavily_agent_result["agent_outcome"].return_values["output"])
    tavily_search_result = transform_search_result(search_engine="Tavily", search_result=extract_tavily_agent_result)
    print(f"tavily_agent_result: {tavily_agent_result}")
    return {
        "intermediate_steps": [(state["agent_output"], extract_tavily_agent_result)],
        "search_result": state["search_result"] + "\n\n" + tavily_search_result
    }


def wikipedia_agent_node(state):
    print(f"wikipedia agent node: {state}")
    messages = HumanMessage(content=f"Hi! I'm PAR Project Manager Agent! {state['instructions']}")
    wikipedia_agent_result = PAR_Team_Member_Agent_Wikipedia.invoke({"input": messages})
    extract_wikipedia_agent_result = extract_result(wikipedia_agent_result["agent_outcome"].return_values["output"])
    wikipedia_search_result = transform_search_result(search_engine="Wikipedia", search_result=extract_wikipedia_agent_result)
    print(f"wikipedia_agent_result: {wikipedia_agent_result}")
    return {
        "intermediate_steps": [(state["agent_output"], extract_wikipedia_agent_result)],
        "search_result": state["search_result"] + "\n\n" + wikipedia_search_result
    }


def youtube_agent_node(state):
    print(f"youtube_agent_node: {state}")
    messages = HumanMessage(content=f"Hi! I'm PAR Project Manager Agent! {state['instructions']}")
    youtube_agent_result = PAR_Team_Member_Agent_Youtube.invoke({"input": messages})
    extract_youtube_agent_result = extract_result(youtube_agent_result["agent_outcome"].return_values["output"])
    youtube_search_result = transform_search_result(search_engine="Youtube", search_result=extract_youtube_agent_result)
    print(f"youtube_agent_result: {youtube_agent_result}")
    return {
        "intermediate_steps": [(state["agent_output"], extract_youtube_agent_result)],
        "search_result": state["search_result"] + "\n\n" + youtube_search_result
    }


def arXiv_agent_node(state):
    print(f"arxiv_agent_node: {state}")
    messages = HumanMessage(content=f"Hi! I'm PAR Project Manager Agent! {state['instructions']}")
    arxiv_agent_result = PAR_Team_Member_Agent_ArXiv.invoke({"input": messages})
    extract_arxiv_agent_result = extract_result(arxiv_agent_result["agent_outcome"].return_values["output"])
    arxiv_search_result = transform_search_result(search_engine="ArXiv", search_result=extract_arxiv_agent_result)
    print(f"arxiv_agent_result: {arxiv_agent_result}")
    return {
        "intermediate_steps": [(state["agent_output"], extract_arxiv_agent_result)],
        "search_result": state["search_result"] + "\n\n" + arxiv_search_result
    }


def document_agent_node(state):
    print(f"Document writer agent node: {state}")
    messages = HumanMessage(content=f"Hi! I'm PAR Project Manager Agent! {state['instructions']}")
    document_agent_result = Document_Writer_chain.invoke({"input": messages.content, "search_result": state["search_result"]})
    return {
        "intermediate_steps": [(state["agent_output"], document_agent_result)],
    }


workflow = StateGraph(AgentState)
workflow.add_node("manager", PM_chain)
workflow.add_node("tavily_agent", tavily_agent_node)
workflow.add_node("document_agent", document_agent_node)
workflow.add_node("wikipedia_agent", wikipedia_agent_node)
workflow.add_node("youtube_agent", youtube_agent_node)
workflow.add_node("arxiv_agent", arXiv_agent_node)

for member in members:
    workflow.add_edge(member, "manager")
conditional_map = {k: k for k in members}
conditional_map["FINISH"] = END
workflow.add_conditional_edges("manager", lambda x: x["next"], conditional_map)
workflow.set_entry_point("manager")
project_manager_graph = workflow.compile()

if __name__ == "__main__":
    provided_section = """<section>
<title>Introduction</title>
<explanation>Introduce the importance of asynchronous programming and the role of coroutines in simplifying concurrent code.</explanation>
<content_type>Overview</content_type>
<key_points>
<point>Define asynchronous programming and its challenges</point>
<point>Introduce coroutines as a solution for writing asynchronous code</point>
</key_points>
<search_model>
<search_engine>['tavily_search_results_json']</search_engine>
<search_queries>
<query>asynchronous programming fundamentals</query>
<query>challenges of traditional concurrency models</query>
<query>introduction to coroutines for asynchronous programming</query>
</search_queries>
</search_model>
<search_model>
<search_engine>['wikipedia']</search_engine>
<search_queries>
<query>asynchronous programming</query>
<query>concurrency models</query>
</search_queries>
</search_model>
<synthesis_plan>Use tavily_search_results_json to gather information on asynchronous programming fundamentals and the motivation behind coroutines. Supplement with background context from Wikipedia.</synthesis_plan>
<outline>1. Explain the need for asynchronous programming in modern applications
2. Discuss the limitations of traditional concurrency models like threads and callbacks
3. Briefly introduce coroutines as an alternative approach</outline>
</section>"""
    result = project_manager_graph.invoke({
        "input": f"<provided_section>\n{provided_section}\n</provided_section>",
        "search_result": ""
    })
    print(result)
