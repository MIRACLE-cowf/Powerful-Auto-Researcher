from langchain_anthropic import ChatAnthropic
from langchain_anthropic.experimental import ChatAnthropicTools
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from CustomHelper.Anthropic_helper import CustomAnthropicTools
import os
from dotenv import load_dotenv

load_dotenv()


def get_anthropic_model(model_name="haiku", temperature=0.3) -> ChatAnthropic:
    if model_name == 'sonnet':
        model = "claude-3-sonnet-20240229"
    elif model_name == 'haiku':
        model = "claude-3-haiku-20240307"
    else:
        model = "claude-3-opus-20240229"

    llm = ChatAnthropic(
        model=model,
        temperature=temperature,
        max_tokens=4096,
        anthropic_api_key=os.getenv('ANTHROPIC_API_KEY')
    )
    return llm


def get_anthropic_model_tools_ver(model_name="haiku", temperature=0) -> ChatAnthropicTools:
    if model_name.lower() == 'sonnet':
        model = "claude-3-sonnet-20240229"
    elif model_name.lower() == 'haiku':
        model = "claude-3-haiku-20240307"
    else:
        model = "claude-3-opus-20240229"

    llm = CustomAnthropicTools(
        model=model,
        temperature=temperature,
        max_tokens=4096,
        anthropic_api_key=os.getenv('ANTHROPIC_API_KEY')
    )

    return llm


def get_openai_embedding_model(model_name="small") -> OpenAIEmbeddings:
    if model_name == 'small':
        model = "text-embedding-3-small"
    else:
        model = "text-embedding-3-large"
    embedding = OpenAIEmbeddings(
        model=model,
        openai_api_key=os.getenv('OPENAI_API_KEY')
    )
    return embedding
