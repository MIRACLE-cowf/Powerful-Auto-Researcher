import asyncio
import time
from typing import List, Any, Union

from anthropic import BadRequestError
from langchain_core.documents import Document
from langchain_core.runnables import Runnable, RunnableSerializable

from CustomHelper.Custom_Error_Handler import PAR_ERROR


def get_current_date():
    from datetime import datetime
    current_date = datetime.now().strftime("%Y-%m-%d")
    return current_date


def generate_doc_result(docs: List[Document]):
    doc_results = ""

    if len(docs) == 0:
        return "<no_documents_found>\nThere is no relevant documents in Vector DB\n</no_documents_found>"

    for idx, doc in enumerate(docs, start=1):
        doc_results += f"""\n<document index="{idx}">"""

        if doc.metadata:
            if 'source' in doc.metadata:
                doc_results += f"""
<sources>
<source>{doc.metadata['source']}</source>"""
            if 'page' in doc.metadata:
                doc_results += f"""
<page>{doc.metadata['page']}</page>"""
            if 'source' in doc.metadata or 'page' in doc.metadata:
                doc_results += """
</sources>"""
        doc_results += f"""
<document_content>
{doc.page_content}
</document_content>
</document>"""
    return doc_results


def generate_final_doc_results(documents, index):
    yes_doc_results = ""
    for inner_index, doc in enumerate(documents):
        yes_doc_results += f"""<document index="{inner_index + index}">"""
        if doc.metadata:
            if 'source' in doc.metadata:
                yes_doc_results += f"""
<sources>
<source>{doc.metadata['source']}</source>"""
            if 'page' in doc.metadata:
                yes_doc_results += f"""
<page>{doc.metadata['page']}</page>"""
            if 'source' in doc.metadata or 'page' in doc.metadata:
                yes_doc_results += """
</sources>"""
        yes_doc_results += f"""
<document_content>
{doc.page_content}
</document_content>
</document>"""
    return yes_doc_results


def retry_with_delay(llm: Runnable, max_retries: int = 10, delay_seconds: float = 10.0) -> Any:
    for attempt in range(max_retries):
        try:
            print(f'!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!Attempt {attempt + 1} of {max_retries}!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
            print(llm)
            return llm
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!Attempt {attempt + 1} failed with error: {str(e)}. Retrying in {delay_seconds} seconds...!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                time.sleep(delay_seconds)
            else:
                raise e


async def retry_with_delay_async(
    chain: RunnableSerializable,
    input: Union[dict | list],
    max_retries: int = 5,
    delay_seconds: float = 45.0,
    is_batch: bool = False,
) -> Any:
    for attempt in range(max_retries):
        try:
            if is_batch is True:
                return await chain.abatch(inputs=input, config={'recursion_limit': 100})
            else:
                return await chain.ainvoke(input=input, config={'recursion_limit': 100})

        except BadRequestError as e:
            error_message = str(e)
            if 'Output blocked by content filtering policy' in error_message:
                print("Output blocked by content filtering policy. Skipping retry.")
                raise PAR_ERROR(error_message)
            else:
                if attempt < max_retries - 1:
                    print(f"Bad request error: {error_message}. Retrying in {delay_seconds} seconds...")
                    await asyncio.sleep(delay_seconds)
                else:
                    raise PAR_ERROR(error_message)
        except Exception as e:
            error_message = str(e)
            if attempt < max_retries - 1:
                print(f"!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!Attempt {attempt + 1} failed with error: {str(e)}. Retrying in {delay_seconds} seconds...!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                await asyncio.sleep(delay_seconds)
            else:
                raise PAR_ERROR(error_message)