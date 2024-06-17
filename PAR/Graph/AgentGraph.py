import operator
from typing import TypedDict, Union, Annotated, Dict

from langchain import hub
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.utilities.wikipedia import WikipediaAPIWrapper
from langchain_core.agents import AgentAction, AgentFinish
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolExecutor

from CustomHelper.Anthropic_helper import format_to_anthropic_tool_messages
from CustomHelper.THLO_helper import SectionPlan
from CustomHelper.load_model import get_anthropic_model
from Deprecated.Custom_AnthropicAgentOutputParser import AnthropicAgentOutputParser_beta
from Tool.CustomSearchFunc import web_search, wikipedia_search, youtube_search, arXiv_search
from Tool.CustomSearchTool import Custom_WikipediaQueryRun, Custom_YouTubeSearchTool, Custom_arXivSearchTool
from Tool.Respond_Agent_Section_Tool import FinalResponseTool, FinalResponse_SectionAgent
from Util.Retriever_setup import mongodb_store, parent_retriever

agent_prompt = hub.pull("miracle/par_agent_prompt_public")

#For Agent, highly recommended "sonnet" or "opus" model. It can use "haiku" model, but don't guarantee good results.
llm = get_anthropic_model(model_name="sonnet")

tavilytools = TavilySearchResults()
wikipedia = Custom_WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper())
youtube_search_tool = Custom_YouTubeSearchTool()
arXiv_search_tool = Custom_arXivSearchTool()
response_tool = FinalResponseTool()
tools = [tavilytools, wikipedia, youtube_search_tool, arXiv_search_tool, response_tool]
chain = (
    {
        "input": lambda x: x['section_plan'],
        "agent_scratchpad": lambda x: format_to_anthropic_tool_messages(x['intermediate_steps']),
    }
    | agent_prompt.partial(add_more_restrictions="3. ALWAYS use 'Final-Respond' tool only when all the information about the section has been collected and you are ready to finally inform the user of all the information about the section. If you do not use this tool, you will not be able to forward the results to users, and so you will be penalized.")
    | llm.bind_tools(tools=tools)
    | AnthropicAgentOutputParser_beta()
)


class AgentState(TypedDict):
    order: int
    original_question: str
    section_plan: SectionPlan
    agent_outcome: Union[AgentAction, AgentFinish, None]
    intermediate_steps: Annotated[list[tuple[AgentAction, str]], operator.add]
    keys: Dict[str, any]
    final_respond: FinalResponse_SectionAgent


def run_agent(data):
    """Running Agent stage"""
    print('---RUN AGENT---')
    section_plan = data['section_plan'].as_str()
    intermediate_steps = data['intermediate_steps']
    agent_outcome = chain.invoke({'section_plan': section_plan, 'intermediate_steps': intermediate_steps})

    if isinstance(agent_outcome, list) and len(agent_outcome) > 0:
        return { "agent_outcome": agent_outcome[0] }
    elif isinstance(agent_outcome, AgentFinish):
        return { "agent_outcome": agent_outcome }
    else:
        raise ValueError(f"Unexpected agent_outcome: {agent_outcome}")


def router(data):
    print('---ROUTER---')
    if isinstance(data['agent_outcome'], AgentFinish):
        return 'end'
    else:
        return 'tools'


def retry_node(data):
    """In previous versions, claude model is answering "Try Again!. So I put this stages, maybe it will be deprecated."""
    print('---RETRY NODE---')
    data['intermediate_steps'] = []
    return data


tool_executor = ToolExecutor(tools)


def execute_tools(data):
    """Executing tools stage"""
    print('---EXECUTE TOOLS---')
    agent_action = data['agent_outcome']
    tool_name = agent_action.tool
    if tool_name == 'tavily_search_results_json':
        return { 'keys': { 'tool': 'tavily', 'tool_input': agent_action.tool_input }}
    elif tool_name == 'wikipedia':
        return { 'keys': { 'tool': 'wikipedia', 'tool_input': agent_action.tool_input}}
    elif tool_name == 'youtube_search':
        return { 'keys': { 'tool': 'youtube', 'tool_input': agent_action.tool_input}}
    elif tool_name == 'arXiv_search':
        return { 'keys': { 'tool': 'arXiv', 'tool_input': agent_action.tool_input}}
    elif tool_name == "section_complete":
        return { 'keys': { 'tool': "section_complete", 'tool_input': agent_action.tool_input }}
    else:
        return { 'keys': { 'tool': 'retry' }}


def router_tool(data):
    """Routing Tools stage"""
    if data['keys']['tool'] == 'tavily':
        return 'tavily'
    elif data['keys']['tool'] == 'wikipedia':
        return 'wikipedia'
    elif data['keys']['tool'] == 'youtube':
        return 'youtube'
    elif data['keys']['tool'] == 'arXiv':
        return 'arXiv'
    elif data['keys']['tool'] == 'section_complete':
        return 'respond'
    else:
        return 'retry'



def tavily_search_node(data):
    """TAVILY search node stage"""
    print('---TAVILY SEARCH NODE---')
    agent_action = data['agent_outcome']
    result = web_search(
        query=data['keys']['tool_input']['query'],
        datastore=mongodb_store,
        retriever=parent_retriever
    )
    return {
        'intermediate_steps': [(agent_action, result)]
    }


def wikipedia_search_node(data):
    """WIKIPEDIA search node stage"""
    print('---WIKIPEDIA SEARCH NODE---')
    agent_action = data['agent_outcome']
    return {
        'intermediate_steps': [(agent_action, wikipedia_search(data['keys']['tool_input']['query']))]
    }


def youtube_search_node(data):
    """YOUTUBE search node stage"""
    print('---YOUTUBE SEARCH NODE---')
    agent_action = data['agent_outcome']
    return {
        'intermediate_steps': [(agent_action, youtube_search(data['keys']['tool_input']['query']))]
    }


def arXiv_search_node(data):
    """ARXIV search node stage
    In ARXIV search, we use LLM for summary and extract relevant information"""
    print('---ARXIV SEARCH NODE---')
    agent_action = data['agent_outcome']
    original_question = data['original_question']
    section_plan = data['section_plan']
    arXiv_result = arXiv_search(
        query=data['keys']['tool_input']['query'],
        original_question=original_question,
        provided_section=section_plan.as_str_title_explanation()
    )
    return {
        'intermediate_steps': [(agent_action, arXiv_result)]
    }


def respond_node(data):
    """Respond node stage"""
    print('---RESPOND NODE---')
    return {
        "final_respond": FinalResponse_SectionAgent(
            section_title=data['keys']['tool_input']['section_title'],
            section_content=data['keys']['tool_input']['section_content'],
            section_thought=data['keys']['tool_input']['section_thought'],
        ),
        "order": data["order"]
    }


workflow = StateGraph(AgentState)
workflow.add_node('agent', run_agent)
workflow.add_node('retry', retry_node)
workflow.add_node('action', execute_tools)
workflow.add_node('tavily', tavily_search_node)
workflow.add_node('wikipedia', wikipedia_search_node)
workflow.add_node('youtube', youtube_search_node)
workflow.add_node('arXiv', arXiv_search_node)
workflow.add_node("respond", respond_node)
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
        'arXiv': 'arXiv',
        'respond': 'respond',
        'retry': 'retry'
    }
)
workflow.add_edge('retry', 'agent')
workflow.add_edge('tavily', 'agent')
workflow.add_edge('wikipedia', 'agent')
workflow.add_edge('youtube', 'agent')
workflow.add_edge('arXiv', 'agent')
workflow.set_finish_point('respond')
search_graph= workflow.compile().with_config(run_name="Agent Auto Search")