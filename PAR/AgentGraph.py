import operator
from typing import TypedDict, Union, Annotated, Dict
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.utilities.wikipedia import WikipediaAPIWrapper
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain import hub
from langchain_core.agents import AgentAction, AgentFinish
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolExecutor

from CustomHelper.Anthropic_helper import convert_tools, convert_intermediate_steps
from CustomHelper.Custom_AnthropicAgentOutputParser import AnthropicAgentOutputParser_v2
from CustomHelper.load_model import get_anthropic_model_tools_ver
from CustomSearchFunc import web_search, wikipedia_search, youtube_search, arXiv_search
from CustomSearchTool import Custom_WikipediaQueryRun, Custom_YouTubeSearchTool, Custom_arXivSearchTool


class Tool(BaseModel):
    tool_name: str = Field(
        description="Tool name",
    )
    tool_input: str = Field(
        description="Tool input"
    )

agent_prompt = hub.pull("miracle/par_agent_prompt")
llm_with_tools = get_anthropic_model_tools_ver(model_name="sonnet")
tavilytools = TavilySearchResults()
wikipedia = Custom_WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper())
youtube_search_tool = Custom_YouTubeSearchTool()
arXiv_search_tool = Custom_arXivSearchTool()
tools = [tavilytools, wikipedia, youtube_search_tool, arXiv_search_tool]
chain = (
    {
        "input": lambda x: x['input'],
        "agent_scratchpad": lambda x: convert_intermediate_steps(x['intermediate_steps']),
    }
    | agent_prompt.partial(tools=convert_tools(tools))
    | llm_with_tools.bind_tools(tools=tools).bind(stop=["</function_calls>", "</invoke>"])
    | AnthropicAgentOutputParser_v2()
)

class AgentState(TypedDict):
    input: str
    agent_outcome: Union[AgentAction, AgentFinish, None]
    intermediate_steps: Annotated[list[tuple[AgentAction, str]], operator.add]
    keys: Dict[str, any]


def run_agent(data):
    print('---RUN AGENT---')
    if isinstance(data['agent_outcome'], AgentFinish):
        if 'Try Again!' in data.get('agent_outcome').return_values['output']:
            data['intermediate_steps'] = []
    agent_outcome = chain.invoke(data)
    return { "agent_outcome": agent_outcome }


def router(data):
    print('---ROUTER---')
    if isinstance(data['agent_outcome'], AgentFinish):
        if "Try Again!" in data['agent_outcome'].return_values['output']:
            return "retry"
        else:
            return "end"
    else:
        return 'tools'


def retry_node(data):
    print('---RETRY NODE---')
    data['intermediate_steps'] = []
    return data


tool_executor = ToolExecutor(tools)


def execute_tools(data):
    agent_action = data['agent_outcome']
    tool_name = agent_action.tool
    if tool_name == 'tavily_search_results_json':
        return { 'keys': { 'tool': 'tavily', 'tool_input': agent_action.tool_input }}
    elif tool_name == 'wikipedia':
        return { 'keys': { 'tool': 'wikipedia', 'tool_input': agent_action.tool_input}}
    elif tool_name == 'youtube_search':
        return { 'keys': { 'tool': 'youtube', 'tool_input': agent_action.tool_input}}
    else:
        return { 'keys': { 'tool': 'arXiv', 'tool_input': agent_action.tool_input}}
    # output = tool_executor.invoke(agent_action)
    # return { 'intermediate_steps': [(agent_action, str(output))]}


def router_tool(data):
    if data['keys']['tool'] == 'tavily':
        return 'tavily'
    elif data['keys']['tool'] == 'wikipedia':
        return 'wikipedia'
    elif data['keys']['tool'] == 'youtube':
        return 'youtube'
    else:
        return 'arXiv'


def tavily_search_node(data):
    print('---TAVILY SEARCH NODE---')
    agent_action = data['agent_outcome']
    return {
        'intermediate_steps': [(agent_action, web_search(data['keys']['tool_input']['query']))]
    }


def wikipedia_search_node(data):
    print('---WIKIPEDIA SEARCH NODE---')
    agent_action = data['agent_outcome']
    return {
        'intermediate_steps': [(agent_action, wikipedia_search(data['keys']['tool_input']['query']))]
    }


def youtube_search_node(data):
    print('---YOUTUBE SEARCH NODE---')
    agent_action = data['agent_outcome']
    return {
        'intermediate_steps': [(agent_action, youtube_search(data['keys']['tool_input']['query']))]
    }


def arXiv_search_node(data):
    print('---ARXIV SEARCH NODE---')
    agent_action = data['agent_outcome']
    return {
        'intermediate_steps': [(agent_action, arXiv_search(data['keys']['tool_input']['query']))]
    }


workflow = StateGraph(AgentState)
workflow.add_node('agent', run_agent)
workflow.add_node('retry', retry_node)
workflow.add_node('action', execute_tools)
workflow.add_node('tavily', tavily_search_node)
workflow.add_node('wikipedia', wikipedia_search_node)
workflow.add_node('youtube', youtube_search_node)
workflow.add_node('arXiv', arXiv_search_node)
workflow.set_entry_point('agent')
workflow.add_conditional_edges(
    "agent",
    router,
    {
        'end': END,
        'tools': 'action',
        'retry': 'retry'
    }
)
workflow.add_conditional_edges(
    'action',
    router_tool,
    {
        'tavily': 'tavily',
        "wikipedia": 'wikipedia',
        'youtube': 'youtube',
        'arXiv': 'arXiv'
    }
)
workflow.add_edge('retry', 'agent')
workflow.add_edge('tavily', 'agent')
workflow.add_edge('wikipedia', 'agent')
workflow.add_edge('youtube', 'agent')
workflow.add_edge('arXiv', 'agent')
search_graph= workflow.compile().with_config(run_name="Agent Auto Search")