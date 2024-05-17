import os

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

load_dotenv()


# def get_cohere_model(model_name="command-r", temperature=0) -> ChatCohere:
#     llm = ChatCohere(
#         model=model_name,
#         temperature=temperature
#     )
#     return llm


def get_anthropic_model(model_name="haiku", temperature=0.3) -> ChatAnthropic:
    """Load the Anthropic model easily. You can freely revise it to make it easier to use."""
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
        anthropic_api_key=os.getenv('ANTHROPIC_API_KEY'),
        default_headers={"anthropic-beta": "tools-2024-04-04"}
    )
    return llm


def get_openai_model(model_name="gpt3.5", temperature=0.3) -> ChatOpenAI:
    if model_name == 'gpt4':
        model = "gpt-4o-2024-05-13"
    else:
        model = "gpt-4-turbo-2024-04-09"

    llm = ChatOpenAI(
        model_name=model,
        temperature=temperature,
        max_tokens=4096,
        openai_api_key=os.getenv('OPENAI_API_KEY'),
    )
    return llm


def get_openai_embedding_model(model_name="small") -> OpenAIEmbeddings:
    """Load the OpenAI embedding model easily. You can freely revise it to make it easier to use."""
    if model_name == 'small':
        model = "text-embedding-3-small"
    else:
        model = "text-embedding-3-large"
    embedding = OpenAIEmbeddings(
        model=model,
        openai_api_key=os.getenv('OPENAI_API_KEY')
    )
    return embedding
