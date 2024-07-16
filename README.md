# Powerful-Auto-Researcher(PAR)

## 👋 Introduction 👋
Hello! I am a beginner developer who is greatly interested in the rapidly emerging field of LLMs.

This is an experimental project in its early stages, created for the purpose of studying LLM prompting and Python for my own study.  
However, I believe it to be quite an intriguing idea, and I wish to receive ample feedback and opinions from the brilliant developers on GitHub, while honing my development skills!!

There's a new update! The performance is better than expected compared to the previous version, so I've rewritten the README!

Thank you for starred this project!

Thank you for coming by, and please keep an eye out for future updates!

## 🌠 OverView 🌠
This project **PAR** is an advanced automated researcher system powered by [LangChain](https://github.com/langchain-ai/langchain), [LangGraph](https://github.com/langchain-ai/langgraph), and _**Large Language Model(LLM)**_ technologies.  
The **PAR** goes beyond traditional RAG(Retrieval-Augmented Generation) systems, offering not only more powerful and efficient information retrieval but also document generation capabilities.  
It aims to achieve highly accurate and efficient information retrieval and document generation by prompting the LLM to consider human perspectives, _such as why a particular question might be asked_ or _what information a human might desire_.  
Utilizing a wide range of search engines and data sources, The PAR collects comprehensive information and then automatically generates high-quality documents based on this collected data. These documents are then embedded and stored in a vector database for optimized future retrieval.

The PAR project seeks to efficiently extract and organize essential knowledge from the vast sea of information, aiming to transform the paradigm of knowledge work across various fields, including researchers, students, and business professionals.


While the project is still in its early experimental stages and there are many steps that I ahead, it is an endeavor that I would like to share with the brilliant developers on GitHub, discussing exciting ideas and possibilities!

**Before you start, you can see Test Case and Result in [Test_Case](./Test_Case) folder!**

| Version    | Average Time      | Average Token                    | Document Quality |
|------------|-------------------|----------------------------------|------------------|
| 2024.04.02 | About 30 ~ 40 min | About 600,000 ~ 1,100,000 tokens | 1.5 ~ 2          |
| 2024.05.30 | About 7 ~ 15 min  | About 125,000 ~ 750,000 tokens   | 2.5 ~ 4          |
+ This evaluation is extremely **subjective**.

## 😉 Help Me & Discuss Me 😉
If you would like to see the results of the document generation, please leave a comment in the designated issue. I will be happy to provide you with the generated documents for your review.
Or you can freely leave any comments in `Dicussions`!


## 🌠 Contents 🌠
Before getting start, strongly recommend that you read through the contents thoroughly!

1. [**Detailed**](MarkDown/OverView.md)
2. [**How Does It Work?**](MarkDown/How-Does-It-Work.md)
3. [**All Flow Chart**](MarkDown/FlowChart.md#all-flowchart)



## 🚀 HOW TO START 🚀

### ❗WARNING❗❗WARNING❗❗WARNING❗
### **This project may use so many tokens, so be careful!**
### ❗WARNING❗❗WARNING❗❗WARNING❗


### 🤝 Main Third-party libraries 🤝

#### 1. [LangChain(Main Interface)](https://github.com/langchain-ai/langchain)
#### 2. [LangGraph(Recursive structure and Clear flow)](https://github.com/langchain-ai/langgraph)
#### 3. [LangSmith(Debugging)](https://docs.smith.langchain.com/)
#### 4. [Anthropic(Language Model)](https://docs.anthropic.com/claude/docs/models-overview#claude-3-a-new-generation-of-ai)
#### 5. [OpenAI(Embedding Model)](https://platform.openai.com/docs/models/embeddings)
#### 6. [Tavily API(Main Search Engine)](https://docs.tavily.com/docs/tavily-api/introduction)
#### 7. [PineCone(Vector Store)](https://www.pinecone.io/)
* Vector store provided by LangChain, freely usable with any [vector store supported by LangChain](https://python.langchain.com/docs/integrations/vectorstores). For testing, please use an any Online Vector Store!
#### 8. [MongoDB(BaseStore)](https://www.mongodb.com/)
* 2024.04.06 added -> In the future, will use ParentDocumentRetriever.
#### 9. YouTube Search(Main Search Engine)
#### 10. Wikipedia(Main Search Engine)
#### 11. arXiv(Main Search Engine)
#### 12. [Brave Search(Main Search Engine)](https://brave.com/search/api/)
#### 13. [AskNews(Main Search Engine)](https://asknews.app/en)


### 🎯 Try it 🎯
The main libraries required for running the project can be found in the **requirements.txt** file.

1. Clone this repository
```Bash
git clone https://github.com/MIRACLE-cowf/Powerful-Auto-Researcher.git
```

2. Move to the cloned repository
```Bash
cd Powerful-Auto-Researcher
```

3. Inside the `Powerful-Auto-Researcher`, fill in the necessary **API** keys in the `.env` file
    - **LangChain**
    - **AskNews**
    - **Anthropic**
    - **Tavily**
    - **Brave Search**
    - **AskNews**
    - **PineCone**
    - **Mongo DB**

4. Install the required libraries
```Bash
pip install -r requirements.txt 
```

5. Run main.py
```Bash
python3 -m main
```


## ✅ Update Log ✅
### 2024.05.30
- Update New Version with New README
### 2024.04.11
- Now you can find new test cases that have been added after each update in the issue tracker!
### 2024.04.10
- New updates are now being managed through the GitHub issue tracker. You can check it!
- Project changes, bug tracking, feature requests, and more can be effectively tracked and documented using issues.
- In addition to the update log, various topics will be managed systematically through the use of issues.
- Please refer to the GitHub issues for future updates and changes.
### 2024.04.06
- With the official support for Tool Calling from Anthropic and the corresponding update to LangChain, the function calling has been changed from using XML tags to the official function calling method.
- With the availability of official tool calling, there have been modifications to the LangSmith prompts and several new classes have been introduced for structured output.
- In the Retrieve Vector DB stage, I plan to use LangChain's ParentDocumentRetrieve beyond simple similarity search, so preliminary work has been done to enable the use of MongoDB.
- To fetch the Raw content and AI responses from the Tavily API, I have customized the TavilySearchResults function in LangChain.
- For smooth usage of Anthropic's agent, I have customized the OutputParser provided by LangChain.


### 2024.04.02
- Project First Init


## 🔥 FeedBack 🔥
As a beginner developer, I am greatly seeking diverse feedback from the brilliant developers on GitHub!

I would appreciate any kind of feedback, regardless of the type, be it Python syntax, structure, prompting, readme, etc.!

Or you can freely leave comment at **`Issue`** or **`Dicussion`**!

적극적인 피드백 부탁드립니다!

Thank you!  
miracle.cowf@gmail.com

