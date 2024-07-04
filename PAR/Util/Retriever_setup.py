import os
from dotenv import load_dotenv
from langchain.retrievers import ParentDocumentRetriever
from langchain_community.storage.mongodb import MongoDBStore
from langchain_pinecone import PineconeVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter

from PAR.CustomHelper.load_model import get_openai_embedding_model

load_dotenv()

mongoDBURI = os.getenv("MONGODB_URI")
mongoDB_name = os.getenv("MONGODB_NAME")
mongoDB_collection = os.getenv("MONGODB_COLLECTION")
pinecone_index_name = os.getenv("PINECONE_INDEX_NAME")


mongodb_store = MongoDBStore(connection_string=mongoDBURI, db_name=mongoDB_name, collection_name=mongoDB_collection)


embedding = get_openai_embedding_model(model_name="large") # Replace your prefer embedding model
vectorstore = PineconeVectorStore(index_name=pinecone_index_name, embedding=embedding)


# This will be update soon!
child_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
parent_retriever = ParentDocumentRetriever(
    vectorstore=vectorstore,
    docstore=mongodb_store,
    child_splitter=child_splitter,
)

