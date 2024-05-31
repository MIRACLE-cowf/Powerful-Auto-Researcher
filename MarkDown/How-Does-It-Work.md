## 💻 How does Powerful-Auto-Researcher (PAR) work? 💻
PAR is fundamentally designed to start with the user's question, convert it into multi-queries, and leverage the existing vector DB data sources possessed by the user or developer.

**It's better to look at it together with the [FlowChart](FlowChart.md#multi-agent)!**

### 💫 **Transform New Query**
This step modifies the user's question query to fit the PAR project as English, regardless of the language in which the user initially inputs the question.  
The subsequent steps until the final step are carried out using this modified question.

### 👾 **Multi-Query-Generate**
To search the vector DB using the question query optimized for the PAR project generated in the previous step, the question is transformed into three different questions with distinct purposes:
1. Regenerate a related search query focusing on the core aspects of the original question.
2. Regenerate a query using semantically similar phrases to the original question.
3. Regenerate a new query expanding on the potential intent behind the original question.


### 🔍 **Vector DB Search**
For each of the three generated queries, a search is conducted in the user's current vector DB, and the search results are retrieved. In the current project, the PineCone Online Vector Database is used, and a maximum of three search results are obtained for each query.


### 💯 **Grade**
The LLM evaluates the vector DB search results for each of the three queries. After the evaluation, similar to a typical RAG system, the results are used to either generate a response(**Generation**) or move to the **Parallel Execution** stage.  
(This part is currently under consideration and design to explore more possibilities.)

### 🛠 **Parallel Execution**
The **Thought-High-Level-Outline** and **Fast Search** steps are executed in parallel.
Looking at the [FlowChart](FlowChart.md#parallel-execution) together makes it easier to understand!

When there was only the **Thought-High-Level-Outline** step, it took a considerable amount of time.
To prevent this waste, the **Fast Search** step was newly introduced, and it follows the general form of **RAG**.

After **Fast Search**, the user is asked whether to continue with the **Deep Search (THLO)** step.
- If the user chooses to stop at this point, the process ends immediately based on the **Fast Search** results.
- If the user chooses to continue, the **THLO** step proceeds.
> In other words, this step is where the THLO step is being executed together.

#### 🚅 **Fast Search**
Fast search is conducted using only two search engines, `Tavily` and `Brave Search`, and a response is provided based on the results.
> No documents are generated in this step!

#### 📚 **Thought-High-Level-Outline**
(This **Thought-High-Level-Outline** part is also under consideration and design to explore more possibilities and exciting experiments.)  
I think this is considered the most powerful part of this project.  
It combines three different smaller components implemented as a LangGraph:
- 📗 **Think & Inner monologue**: The LLM "thinks" about why the user asked the question and what content the LLM itself would like to see included in the final document if it were the user.
- 📘 **Create a draft & outline**: Based on the thoughts from the previous step, a high-level draft of the document is generated. This step focuses on creating a high-level outline rather than a completed draft.
- 📋 **Generate search queries and select/assign tools**: Based on the high-level outline for each section generated in the previous step, this step determines what content to search for in each section and what queries to use with the given search engines.

These three steps are inspired by the STORM architecture in LangGraph.

Also, these steps can be interpreted differently as being similar to the process of creating a **Plan** in **Plan-and-Execute** Architecture.

### 🦾 **Multi Agent**
The previous version had a single agent equipped with multiple search engines as tools and performed searches. Also, in the previous version, the approach was to generate the next section after completing one section.
This resulted in a significant amount of time (about 30-40 minutes) and token consumption (about 700,000 - 1,100,000 tokens).

To prevent the waste of time and tokens, [Multi Agent](https://langchain-ai.github.io/langgraph/tutorials/multi_agent/agent_supervisor/) was newly introduced.

As described on the webpage, it is an architecture where one agent acting as a `supervisor` directs `team member` agents and they work together to produce results.

It's better to look at it together with the [FlowChart](FlowChart.md#multi-agent)!

#### 👊 Team Member
In the PAR project, the following `team member` agents exist:
1. **Tavily**
2. **Brave Search**
3. **Wikipedia**
4. **YouTube**
5. **ArXiv**
6. **AskNews**
7. **Document Generator**

- Each team member agent is equipped with only one search engine, which encourages the LLM to focus solely on its own role. It's better to look at it together with the [FlowChart](FlowChart.md#each-search-agent)!
- The `Document Generator` generates the final **content** for each section by combining the search results from each search agent.

### 📜 **Conclusion Generator**
This is a newly introduced step to ensure document consistency.

In this step, based on all the content generated for each section, only the part corresponding to the `conclusion` of the document is written.
- **Multi Agent** is not introduced in this step, and no **search** is performed. It simply writes the conclusion based on the content of all the previous sections.

### ✉️ **Generation**
This step is similar to the typical G(Generation) step in RAG. This step generates the final response based on the completed document.
- If coming from the ***Grade*** stage, the response is generated based on the contents searched from the Vector DB.  
- If coming from the ***Thought-High-Level-Outline*** stage, the response is generated based on the document created through the previous stages.

~~Before generating the response, the user can decide whether to review and store the generated document in the vector DB.~~
(The process of storing in the vector DB is currently under research!)
