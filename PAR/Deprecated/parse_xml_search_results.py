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