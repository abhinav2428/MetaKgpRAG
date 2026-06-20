import json
import os
from pathlib import Path
from typing import List, Dict
import chromadb
from chromadb.utils import embedding_functions
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    from langchain.text_splitter import RecursiveCharacterTextSplitter
from config.settings import settings


class MetaKGPIndexer:
    def __init__(self):
        self.client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir
        )
        self.ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=settings.embedding_model
        )
        self.collection = self.client.get_or_create_collection(
            name="metakgp_pages",
            embedding_function=self.ef,
            metadata={"hnsw:space": "cosine"},
        )
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def index_page(self, page: Dict) -> int:
        """
        Chunk a page and upsert all chunks into ChromaDB.
        Returns number of chunks indexed.
        """
        chunks = self.splitter.split_text(page["text"])
        if not chunks:
            return 0

        ids, docs, metas = [], [], []
        for i, chunk in enumerate(chunks):
            chunk_id = f"{page['url']}#chunk{i}"
            ids.append(chunk_id)
            docs.append(chunk)
            metas.append({
                "url": page["url"],
                "title": page["title"],
                "chunk_index": i,
                "total_chunks": len(chunks),
                "categories": ", ".join(page.get("categories", [])),
            })

        # upsert is idempotent — safe to re-run
        self.collection.upsert(ids=ids, documents=docs, metadatas=metas)
        return len(chunks)

    def index_all(self, clean_dir: str = None) -> int:
        clean_dir = clean_dir or settings.clean_data_dir
        files = list(Path(clean_dir).glob("*.json"))
        print(f"[Indexer] Indexing {len(files)} pages...")

        total_chunks = 0
        for filepath in files:
            with open(filepath, encoding="utf-8") as f:
                page = json.load(f)
            n = self.index_page(page)
            total_chunks += n
            print(f"  ✓ {page['title']} → {n} chunks")

        count = self.collection.count()
        print(f"[Indexer] Done. {count} total chunks in ChromaDB.")
        return count

    def stats(self) -> Dict:
        return {"total_chunks": self.collection.count()}