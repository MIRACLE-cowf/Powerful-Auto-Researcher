from typing import List

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



class SearchResult:
    def __init__(self, name, explanation, search_queries):
        self.name = name
        self.explanation = explanation
        self.search_queries = search_queries

    def __repr__(self):
        return f"Section(name='{self.name}', explanation='{self.explanation}', search_queries={self.search_queries})"


def parse_search_result(xml_string):
    lines = xml_string.strip().split('\n')
    sections = []
    current_section = None

    for i, line in enumerate(lines):
        if line.startswith('<section'):
            if current_section:
                sections.append(SearchResult(**current_section))
            name = line.split('name="')[1].split('"')[0]
            current_section = {'name': name, 'explanation': '', 'search_queries': []}
        elif line.startswith('<search_query>'):
            search_query = line.replace('<search_query>', '').replace('</search_query>', '').strip()
            search_engine = next(filter(lambda x: x.startswith('<search_engine>'), lines[lines.index(line)+1:]), '').replace('<search_engine>', '').replace('</search_engine>', '').strip()
            current_section['search_queries'].append({'search_query': search_query, 'search_engine': search_engine})
        elif line.startswith('<explanation>'):
            if '</explanation>' in line:
                explanation = line.split('<explanation>')[1].split('</explanation>')[0].strip()
                current_section['explanation'] = explanation
            else:
                explanation_lines = []
                j = i + 1
                while j < len(lines) and not lines[j].startswith('</explanation>'):
                    explanation_lines.append(lines[j].strip())
                    j += 1
                explanation = '\n'.join(explanation_lines)
                current_section['explanation'] = explanation
        elif line.startswith('</section>'):
            if current_section:
                sections.append(SearchResult(**current_section))
                current_section = None

    if current_section:
        sections.append(SearchResult(**current_section))

    return sections