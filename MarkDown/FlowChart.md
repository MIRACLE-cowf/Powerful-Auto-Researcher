## 📌 ALL FlowChart 📌
The overall flow chart of PAR is as follows:

```mermaid
%%{init: {'flowchart': {'curve': 'linear'}}}%%
flowchart TD;
	__start__[__start__]:::startclass;
	__end__[__end__]:::endclass;
	transform_new_query([transform_new_query]):::llmclass;
	multi_query_generator([multi_query_generator]):::llmclass;
	retrieve([retrieve_vector_db]):::toolclass;
	grade_documents([grade_each_documents]):::llmclass;
    
    router{router}:::branchclass;
    
    subgraph Parallel Execution
        __subStart__[__start__]:::startclass;
        subgraph THLO
            __subStart1__[__start__]:::startclass;
            thought([Think & Inner monologue]):::llmclass;
            high_level_outline([High Level Outline]):::llmclass;
            generate_search_queries([Generate Search queries]):::llmclass

            __subStart1__ --> thought --> high_level_outline --> generate_search_queries
        end 

        subgraph FastSearch
            __subStart2__[__start__]:::startclass;

            braveSearch([Brave Search]):::toolclass;
            tavilySearch([Tavily Search]):::toolclass;
            generateFastSearch([generate]):::llmclass;

            __subStart2__ --> braveSearch
            __subStart2__ --> tavilySearch

            braveSearch --> generateFastSearch
            tavilySearch --> generateFastSearch
        end

        __subStart__ -.-> __subStart1__
        __subStart__ -.-> __subStart2__
    end

	generate([generate]):::llmclass;

    
	__start__ --> transform_new_query;
    transform_new_query --> multi_query_generator

    multi_query_generator --> retrieve
    multi_query_generator --> retrieve
    multi_query_generator --> retrieve

    retrieve --> grade_documents
    retrieve --> grade_documents
    retrieve --> grade_documents

    grade_documents --> router
    router -."generate".-> generate
    router -."THLO".-> __subStart__

    deepSearchRouter{DeepSearch}:::branchclass;

    generate_search_queries --> deepSearchRouter
    generateFastSearch --> deepSearchRouter
    deepSearchRouter --"No"--> __end__

    subgraph Composable Search
        __startSearch__[__start__]:::startclass
        __endSearch__[__end__]:::endclass

        manager([manager]):::llmclass;
        tavily_agent([tavily_agent]):::llmclass;
        brave_agent([brave_agent]):::llmclass;
        wikipedia_agent([wikipedia_agent]):::llmclass;
        youtube_agent([youtube_agent]):::llmclass;
        arxiv_agent([arxiv_agent]):::llmclass;
        asknews_agent([asknews_agent]):::llmclass;
        document_agent([document_agent]):::gendocclass;
        response([response]):::llmclass;

        __startSearch__ --> manager;
        arxiv_agent --> manager;
        asknews_agent --> manager;
        brave_agent --> manager;
        document_agent --> manager;
        response --> __endSearch__;
        tavily_agent --> manager;
        wikipedia_agent --> manager;
        youtube_agent --> manager;
        manager -.-> tavily_agent;
        manager -.-> document_agent;
        manager -.-> wikipedia_agent;
        manager -.-> youtube_agent;
        manager -.-> arxiv_agent;
        manager -.-> brave_agent;
        manager -.-> asknews_agent;
        manager -. FINISH .-> response;
    end
    deepSearchRouter -."Yes".-> __startSearch__

    generate_conclusion([Generate Conclusion Section]):::llmclass;
    generate_full_document[Generate Full Document]

    __endSearch__ --> generate_conclusion
    generate_conclusion --> generate_full_document
    generate_full_document --> generate

    


    generate --> __end__



    classDef startclass fill:#6600FF;
    classDef endclass fill:#990099;
    classDef llmclass fill:#003399;
    classDef toolclass fill:#339900;
    classDef branchclass fill:#CC0000;
```

### 🛠 Parallel Execution
Looking in detail at the steps that are executed in parallel, following:

**THLO** and **Fast Search** are executed **simultaneously** in **parallel**.
```mermaid
flowchart TB
    __subStart__[__start__]:::startclass;
    subgraph THLO
        __subStart1__[__start__]:::startclass;
        thought([Think & Inner monologue]):::llmclass;
        high_level_outline([High Level Outline]):::llmclass;
        generate_search_queries([Generate Search queries]):::llmclass

        __subStart1__ --> thought --> high_level_outline --> generate_search_queries
    end

    subgraph FastSearch
        __subStart2__[__start__]:::startclass;

        braveSearch([Brave Search]):::toolclass;
        tavilySearch([Tavily Search]):::toolclass;
        generateFastSearch([generate]):::llmclass;

        __subStart2__ --> braveSearch
        __subStart2__ --> tavilySearch

        braveSearch --> generateFastSearch
        tavilySearch --> generateFastSearch
    end

    __subStart__ -.-> __subStart1__
    __subStart__ -.-> __subStart2__
    classDef startclass fill:#6600FF;
    classDef endclass fill:#990099;
    classDef llmclass fill:#003399;
    classDef toolclass fill:#339900;
    classDef branchclass fill:#CC0000;
```


### 🦾 Multi Agent
Looking at the steps where multiple agents collaborate with each other, have the following:

```mermaid
flowchart TB
    __startSearch__[__start__]:::startclass
    __endSearch__[__end__]:::endclass

    manager([manager]):::llmclass;
    tavily_agent([tavily_agent]):::llmclass;
    brave_agent([brave_agent]):::llmclass;
    wikipedia_agent([wikipedia_agent]):::llmclass;
    youtube_agent([youtube_agent]):::llmclass;
    arxiv_agent([arxiv_agent]):::llmclass;
    asknews_agent([asknews_agent]):::llmclass;
    document_agent([document_agent]):::gendocclass;
    response([response]):::llmclass;

    __startSearch__ --> manager;
    arxiv_agent --> manager;
    asknews_agent --> manager;
    brave_agent --> manager;
    document_agent --> manager;
    response --> __endSearch__;
    tavily_agent --> manager;
    wikipedia_agent --> manager;
    youtube_agent --> manager;
    manager -.-> tavily_agent;
    manager -.-> document_agent;
    manager -.-> wikipedia_agent;
    manager -.-> youtube_agent;
    manager -.-> arxiv_agent;
    manager -.-> brave_agent;
    manager -.-> asknews_agent;
    manager -. FINISH .-> response;

    classDef startclass fill:#6600FF;
    classDef endclass fill:#990099;
    classDef llmclass fill:#003399;
    classDef toolclass fill:#339900;
    classDef branchclass fill:#CC0000;
```

- The agent corresponding to the `manager`, based on the plan for each section generated in the **THLO** step, creates instructions for writing the content of that section and delivers them to the agents specialized in each search engine.
- Finally, when the search is completed, the `document_agent` is called to write the content for the section.


### ⚙ Each Search Agent
The agents specialized in each search engine go through the following detailed steps:

```mermaid
flowchart TB
    __start__[__start__]:::startclass;
    __end__[__end__]:::endclass;
    search_agent([search_agent]):::llmclass;
    search_tool([search_tool]):::toolclass;
    feedback_agent([feedback_agent]):::llmclass;
    __start__ --> search_agent;
    feedback_agent --> search_agent;
    search_tool --> feedback_agent;
    search_agent -. end .-> __end__;
    search_agent -.-> search_tool;
    classDef startclass fill:#6600FF;
    classDef endclass fill:#990099;
    classDef llmclass fill:#003399;
    classDef toolclass fill:#339900;
```

- When the search agent receives **instructions** through the `manager agent`, it starts the search through the tool based on the instructions.
- The searched content is organized on the client-side in the `search_tool` step and then passed to the `feedback_agent`.
- The `feedback_agent` evaluates the searched content and then passes it back to the search agent.
- The search agent decides whether to proceed with a new search query based on the feedback content or to terminate the search.