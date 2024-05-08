from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from CustomHelper.Anthropic_helper import format_to_anthropic_tool_messages
from CustomHelper.Custom_AnthropicAgentOutputParser import AnthropicAgentOutputParser_beta
from CustomHelper.Helper import retry_with_delay


def select_prompt_template(agent_specific_role: str) -> dict:
    if agent_specific_role.lower() == 'tavily':
        search_engine = "Tavily"
        search_engine_description = "The Tavily Search API optimizes the most relevant information from online sources in a single API call, tailored to the context limitations of LLMs. It also supports better decision-making by returning answers to questions or suggesting follow-up search queries."
        search_query_tip = "To find in-depth information on a specific domain, field, or knowledge, it is good to use 'search terms' centered around related core concepts, principles, and examples. 'Search keywords' are also not bad."
    elif agent_specific_role.lower() == 'wikipedia':
        search_engine = "Wikipedia"
        search_engine_description= "The Wikipedia API is a tool that searches Wikipedia to answer general questions on a wide range of topics. It is useful for finding information about people, places, companies, facts, historical events, and more. It takes a search query as input and returns a summary of relevant Wikipedia content."
        search_query_tip = "To find basic information such as concepts, definitions, and features, 'search keywords' directly related to the topic are good."
    elif agent_specific_role.lower() == 'youtube':
        search_engine = "YouTube"
        search_engine_description = "The YouTube Search API allows you to find videos on YouTube related to a given search query. Simply provide a search term or phrase as input, and the API will return a list of relevant video results from YouTube. This tool is helpful when you need to find video content on a specific topic or answer questions that can be addressed by YouTube videos."
        search_query_tip = "To find audiovisual materials or tutorials for a specific domain, field, or knowledge, it is good to use 'search terms' combined with 'search keywords'."
    elif agent_specific_role.lower() == 'arxiv':
        search_engine = "ArXiv"
        search_engine_description = ("The arXiv Search API enables you to search for academic papers on the arXiv preprint repository based on a provided search query. By inputting a search term or "
                                      "phrase, you can quickly find relevant scholarly articles, research papers, and scientific publications hosted on arXiv. This tool is particularly useful for "
                                      "researchers, students, and anyone seeking to access and explore the latest findings and ideas across various scientific disciplines.")
        search_query_tip = "To identify and collect information on scientific fields or the latest research, 'search terms' consisting of core 'keywords' directly related to the topic are good."
    else:
        raise ValueError(f"Unrecognized agent specifier '{agent_specific_role}'")
    return {
        "search_engine": search_engine,
        "search_engine_description": search_engine_description,
        "search_query_tip": search_query_tip
    }


def create_agent(llm: ChatAnthropic, tools: list, agent_specific_role: str):
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a seasoned researcher agent with extensive experience in utilizing the {search_engine} API for data collection and analysis.
Currently, you are a team member of the PAR project, working on writing a specific section of an entire markdown document. The project also involves other team members specialized in different search engines.

Your role is to diligently follow the instruction provided by the Project Manager, effectively coordinate and collaborate with them, and conduct thorough research to contribute to the creation of a perfect section of the document.

<instructions>
1. Thoroughly analyze and execute the instructions received from the Manager Agent.
2. Utilize the {search_engine} search engine to search for relevant information.
- Perform initial searches based on the provided search queries.
- Analyze the search results to assess their relevance to the topic, quality of information, and diversity.
- If necessary, modify or expand the search queries to conduct additional searches.
3. Select the most useful and reliable information from the search results.
- The Manager Agent will rigorously evaluate your results based on their assessment criteria.
- Consider the relevance to the topic, quality and reliability of the information, comprehensiveness and diversity of the content, and usefulness for document creation.
4. Organize the selected search results without summarization and deliver them to the Manager Agent.
- Instead of summarizing, "organize" each search result.
- Provide metadata such as the source, URL, and related keywords for each search result.
- Always include the URL as a reference for each search result to enhance the credibility of the document.
- Analyze the relationships or differences among the search results and provide insights to the Manager Agent.
5. Provide feedback to the Manager Agent if additional searches are required.
- If the initial search results do not yield sufficient information, inform the Manager Agent about the need for additional searches.
- Suggest ideas for additional searches or modified search queries.
</instructions>

<example_final_response_format>
<result>
When delivering the search results to the Manager Agent, please use the following format:

Search Result 1:
Source: [Title or description of the source]
URL: [URL of the search result]
Related Keywords: [Keywords relevant to the search result]
Key Points:
- [Key point 1]
- [Key point 2]
- [Key point 3]
...
Content: [PASTE the relevant content from the search result here without summarization. Include code snippets, explanations, and other important details as they appear in the original source. Do not use placeholders like square brackets.]

Search Result 2:
Source: [Title or description of the source]
URL: [URL of the search result]
Related Keywords: [Keywords relevant to the search result]
Key Points:
- [Key point 1]
- [Key point 2]
- [Key point 3]
...
Content: [PASTE the relevant content from the search result here without summarization. Include code snippets, explanations, and other important details as they appear in the original source. Do not use placeholders like square brackets.]

...


Overall insights:
[Rich insights and analysis of the relationships or differences among the search results]
</result>
</example_final_response_format>

<restrictions>
1. Understand and fully utilize the characteristics and strengths of the {search_engine} search engine and search query tip.
Description: {search_engine_description}
Query Tip: {search_query_tip}
2. Use the allocated time and resources for searching and information organization efficiently.
- Optimize your search strategy to avoid unnecessary searches or duplicate work and focus on key information.
3. Maintain clear and concise communication with the Manager Agent.
- Clearly convey the search results and analysis when delivering them.
- Actively request additional guidance or feedback from the Manager Agent when needed.
4. Always include the actual content from the search results without any summarization and deliver them to the Manager Agent.
- Paste the relevant text, code snippets, explanations, and other important details as they appear in the original source.
- Do not use placeholders like square brackets or omit the content, as this can hinder effective collaboration with other agents.
</result>
</example_final_response_format>


As a {search_engine} search specialized agent, please provide the best search results with relevant URLs and effectively collaborate with the Manager Agent based on the above guidelines and considerations to contribute to the success of the project."""),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad")
    ])
    search_template = select_prompt_template(agent_specific_role=agent_specific_role)
    run_llm = llm.bind_tools(tools=tools).with_fallbacks([llm.bind_tools(tools=tools)] * 5)
    agent_chain = (
        {
            "input": lambda x: x["input"],
            "agent_scratchpad": lambda x: format_to_anthropic_tool_messages(x["intermediate_steps"])
        }
        | prompt.partial(search_engine=search_template["search_engine"], search_engine_description=search_template["search_engine_description"], search_query_tip=search_template["search_query_tip"])
        | retry_with_delay(llm=run_llm, max_retries=7, delay_seconds=45)
        | AnthropicAgentOutputParser_beta()
    )
    return agent_chain

