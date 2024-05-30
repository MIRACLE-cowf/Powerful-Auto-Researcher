from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import BaseTool

from CustomHelper.Anthropic_helper import format_to_anthropic_tool_messages
from CustomHelper.Custom_AnthropicAgentOutputParser_2 import AnthropicAgentOutputParser
from CustomHelper.load_model import get_anthropic_model


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
    elif agent_specific_role.lower() == 'brave':
        search_engine = "BraveSearch"
        search_engine_description = ("Use Brave Search when you need a broad and comprehensive search across a wide range of websites and domains. It is particularly effective for finding the most up-to-date information on current events, trending topics, and rapidly evolving fields. "
                                     "Brave Search crawls and indexes billions of webpages to provide extensive coverage. While it may not always have the same depth as Tavily for academic or highly specialized topics, its strengths lie in its vast reach and ability to surface relevant content from a huge variety of sources. "
                                     "This makes it ideal for queries where a diversity of perspectives and the most current information is desired. Brave Search is also a strong choice when you want a balance of both reliable, high-quality sources and more informal user-generated content like blog posts, social media, forums etc. It provides a well-rounded view. "
                                     "In addition to webpages, Brave Search is effective at finding relevant images, videos, news articles, and other media related to the search. It's useful for things like comprehensive overviews of topics, research on current affairs and pop culture, comparison of different products/services, discovering a range of opinions on issues, and finding real-world examples or applications of concepts.")
        search_query_tip = "For the most relevant results on Brave Search, use specific but concise keyphrases that capture the core elements of your query. Including 1-2 of the most essential keywords is usually sufficient."
    elif agent_specific_role.lower() == 'asknews':
        search_engine = "AskNews"
        search_engine_description = ("Use AskNews when you need the most up-to-date information on current events, breaking news, and trending stories from around the world. AskNews leverages advanced AI techniques to process and index over 300,000 news articles per day from 50,000 diverse sources across 100+ countries and 13 languages.")
        search_query_tip = "Provide as much context as possible about the news topic you're interested in. Mentioning key entities, locations, and timeframes can help narrow down the search."
    else:
        raise ValueError(f"Unrecognized agent specifier '{agent_specific_role}'")
    return {
        "search_engine": search_engine,
        "search_engine_description": search_engine_description,
        "search_query_tip": search_query_tip
    }


def create_agent(llm: ChatAnthropic, tool: BaseTool, agent_specific_role: str):
    fallback_llm = get_anthropic_model(model_name="opus")
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a seasoned researcher agent who has been conducting research using the {search_engine} Search API.

The search engine you use is as follows:
<search_engine_info>
Engine: {search_engine}
Description: {search_engine_description}
Query Tips: {search_query_tip}
</search_engine_info>


You are currently collecting data to write a specific section of the entire document.

The section information you need to investigate is as follows:
<section_info>
{section_info}
</section_info>


Your role now is to diligently carry out the instructions when the project manager delivers them, communicate with the project manager, and perform thorough research to write a specific section.


<instructions>
- Analyze the provided section information.
- Analyze the provided search engine.
- Analyze and execute the instructions received from the manager agent.
- Search for relevant information using the search engine.
	- If search queries are provided in the instructions, perform an initial search based on those queries.
	- Analyze the search results and comprehensively evaluate their relevance to the topic, quality, and diversity of information.
	- If necessary, modify or expand the search terms to perform additional searches.
- Select the most useful and reliable information from the search results.
	- Consider relevance to the section topic, quality and reliability of information, comprehensiveness and diversity of content, and usefulness for document creation.
- **Organize** the search results without summarizing and deliver them to the manager agent.
- Always include URLs as references for each search result to enhance the reliability of the document.
- Provide insights to the manager agent by analyzing the relationships or differences between search results.
</instructions>


<restrictions>
- Understand and fully utilize the features and strengths of the search engine, as you can only use {search_engine} Search.
- Optimize your search strategy to avoid unnecessary searches or duplicated work and focus on key information.
- The manager agent does not share your situation. Therefore, provide clear and detailed search results.
- The manager agent does not share your search results. Therefore, always follow the <example_final_response_format> xml tags below.
- After 'organizing' the search results to include actual content without summarization, deliver it to the manager agent.
	- Paste relevant text, code snippets, descriptions, and other important details as they appear in the original source.
- Do not use placeholders such as square brackets or omit results, as it may interfere with collaboration with the manager agent.
</restrictions>


When delivering search results to the manager agent, use the following format:
<example_final_response_format>
<result>
Search Result 1:
Source: [Title or description of the source]
URL: [URL of the search result]
Relevant Keywords: [Keywords relevant to the search result]
Key Points:

[Key point 1]
[Key point 2]
[Key point 3]
...

Content: [Paste relevant content from the search result here without summarizing. Include code snippets, descriptions, and other important details as they appear in the original source. Do not use placeholders such as square brackets.]
Search Result 2:
Source: [Title or description of the source]
URL: [URL of the search result]
Relevant Keywords: [Keywords relevant to the search result]
Key Points:

[Key point 1]
[Key point 2]
[Key point 3]
...

Content: [Paste relevant content from the search result here without summarizing. Include code snippets, descriptions, and other important details as they appear in the original source. Do not use placeholders such as square brackets.]
...
Overall Insights:
[Rich insights and analysis of relationships or differences between search results]
</result>
</example_final_response_format>
"""),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad")
    ])
    search_template = select_prompt_template(agent_specific_role=agent_specific_role)
    run_llm = llm.bind_tools(tools=[tool]).with_fallbacks([fallback_llm.bind_tools(tools=[tool])] * 3)
    agent_chain = (
        {
            "input": lambda x: x["input"],
            "section_info": lambda x: x["section_info"],
            "agent_scratchpad": lambda x: format_to_anthropic_tool_messages(x["intermediate_steps"])
        }
        | prompt.partial(search_engine=search_template["search_engine"], search_engine_description=search_template["search_engine_description"], search_query_tip=search_template["search_query_tip"])
        | run_llm
        | AnthropicAgentOutputParser()
    )
    return agent_chain

