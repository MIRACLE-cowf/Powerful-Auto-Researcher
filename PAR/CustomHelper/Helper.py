import time
from typing import List, Callable, Any

from langchain_core.documents import Document


def generate_doc_result(docs: List[Document]):
    doc_results = ""

    if len(docs) == 0:
        return "<no_documents_found>There is no relevant documents in Vector DB</no_documents_found>"

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


def retry_with_delay(func: Callable, max_retries: int = 10, delay_seconds: float = 10.0) -> Any:
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            print(f"LLM Retry with delay {delay_seconds} failed due to {str(e)}")
            if attempt < max_retries - 1:
                print(f"Attempt {attempt + 1} failed with error: {str(e)}. Retrying in {delay_seconds} seconds...")
                time.sleep(delay_seconds)
            else:
                raise e