from typing import List, Dict
import chromadb
from chromadb.utils import embedding_functions
from config.settings import settings


class MetaKGPRetriever:
    """
    Semantic retriever over the ChromaDB vector store.
    Returns ranked document chunks with metadata.
    """

    def __init__(self):
        client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=settings.embedding_model
        )
        self.collection = client.get_collection(
            name="metakgp_pages",
            embedding_function=ef,
        )

    def retrieve(self, query: str, n: int = None) -> List[Dict]:
        """
        Query the vector store.
        Returns list of: {document, metadata, distance}
        Lower distance = more similar.
        """
        n = n or settings.top_k_results
        results = self.collection.query(
            query_texts=[query],
            n_results=n,
            include=["documents", "metadatas", "distances"],
        )

        chunks = []
        if results and results["documents"]:
            for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            ):
                chunks.append({
                    "document": doc,
                    "metadata": meta,
                    "distance": dist,
                })

        return chunks