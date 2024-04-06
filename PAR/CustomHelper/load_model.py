from langchain_anthropic import ChatAnthropic
from langchain_anthropic.experimental import ChatAnthropicTools
from langchain_community.chat_models.cohere import ChatCohere
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
import os
from dotenv import load_dotenv

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
        anthropic_api_key=os.getenv('ANTHROPIC_API_KEY')
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
