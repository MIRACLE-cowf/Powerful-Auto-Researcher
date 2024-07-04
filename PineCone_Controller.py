from typing import List

from dotenv import load_dotenv
from langchain.chains.query_constructor.schema import AttributeInfo
from langchain_core.documents import Document
from langchain_pinecone import PineconeVectorStore
from miracle import get_openai_embedding_model

load_dotenv()

index_name = "song"
embeddings = get_openai_embedding_model(model_name="large")
vectorStore = PineconeVectorStore(
	index_name=index_name,
	embedding=embeddings
)
base_retriever = vectorStore.as_retriever()

metadata_field_info = [
	AttributeInfo(
		name="title",
		description="The title of the song.",
		type="string",
	),
	AttributeInfo(
		name="artist",
		description="The artist of the song. Seperated by comma. Can be multiple values, use 'in' comparison statement. Only English and Japanese, none Korean.",
		type="string",
	),
	AttributeInfo(
		name="like",
		description="The like of the song. One of ['liked', 'unliked']",
		type="string",
	),
]


def vectorStore_add_documents(docs: List[Document]):
	vectorStore.add_documents(docs)


def generate_new_documents(_song_description: str, _song_title: str, _artist_name: str,  _lyrics_id: str, _liked: bool = True) -> List[Document]:
	doc = Document(
		page_content=_song_description,
		metadata={
			"title": _song_title,
			"artist": [_artist_name],
			"liked": "liked",
			"lyrics_id": _lyrics_id
		}
	)
	return [doc]