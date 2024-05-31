## 🌠 OverView 🌠
This project aims to build a more powerful RAG system powered by [LangChain](https://github.com/langchain-ai/langchain), [LangGraph](https://github.com/langchain-ai/langgraph), and [Anthropic](https://www.anthropic.com/).  
While the project is still in its early experimental stages and there are many steps that I ahead, it is an endeavor that I would like to share with the brilliant developers on GitHub, discussing exciting ideas and possibilities!

**Before you start, you can see Test Case and Result in [Test_Case](./Test_Case) folder!**

| Version    | Average Time      | Average Token                    | Document Quality |
|------------|-------------------|----------------------------------|------------------|
| 2024.04.02 | About 30 ~ 40 min | About 600,000 ~ 1,100,000 tokens | 1.5 ~ 2          |
| 2024.05.30 | About 7 ~ 15 min  | About 125,000 ~ 750,000 tokens   | 2.5 ~ 4          |
+ This evaluation is extremely **subjective**.



## 🧐 What is RAG(Retrieval-Augmented Generation)? 🧐
Retrieval-Augmented Generation(RAG) is a process that optimizes the output of large language models(LLMs) by enabling them to reference reliable knowledge bases outside of their training data sources before generating responses.  
LLMs are trained on vast amounts of data and use billions of parameters to generate original results for tasks such as answering questions, translating languages, and completing sentences.  
RAG extends the capabilities of already powerful LLMs to the internal knowledge bases of specific domains or organizations, eliminating the need to retrain the model. This is a cost-effective approach to improving LLM results and maintaining relevance, accuracy, and usefulness across a variety of scenarios.




## 👀 So, What is the main difference between RAG and your project PAR(Powerful-Auto-Researcher)? 👀
### 💪 Concept & Features 💪
This PAR Project draws inspiration from various approaches, including:
* [LangChain's Multi-Query-Retriever](https://python.langchain.com/v0.2/docs/how_to/MultiQueryRetriever/)
* [LangGraph - Corrective RAG(CRAG)](https://langchain-ai.github.io/langgraph/tutorials/rag/langgraph_crag/)
* [LangGraph - STORM](https://langchain-ai.github.io/langgraph/tutorials/storm/storm/)
* [Other diverse prompting techniques](https://arxiv.org/abs/2312.16171)
* [LangGraph - Multi Agent Supervisor](https://langchain-ai.github.io/langgraph/tutorials/multi_agent/agent_supervisor/)


This PAR project primarily use Anthropic's Claude 3 family due to their **Long Context Window** capability.  
Although the advent of '**Long Context Window**' has reduced the necessity for **RAG**, this PAR project aims to leverage its advantages beyond the scope of a single document.  
Unlike conventional RAG techniques that extract small token amounts from various sources, PAR seeks to retrieve more substantial token content from diverse origins.  
By processing a large volume of tokens and sources on a single topic simultaneously, the project strives to achieve higher-quality results.

To this end, PAR project employs a prompting approach similar to **Multi-Query-Retriever**, where the user's original question is interpreted from multiple perspectives and reformulated into different question formats on the same topic.  
This enables the model to handle a wider range of thought processes and adaptability, which is the primary objective.


The second powerful aspect of PAR lies in its ability to generate documents autonomously by leveraging custom search engines developed by the project's creators.  
This allows for extensive searches and the utilization of diverse sources such as Tavily, arXiv, YouTube, Wikipedia, and more.

User often invest significant time in conducting searches. To address this issue, PAR aims to integrate results from various search engines to automatically generate documents.  
These documents are made available for users to access later and are embedded and stored in a vector store for future use in identical or similar content searches.
