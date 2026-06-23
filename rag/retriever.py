"""
rag/retriever.py
----------------
A GraphRAG retriever that combines ChromaDB vector search with NetworkX graph traversal.
"""

import argparse
import pickle
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer
import networkx as nx

CHROMA_DB_DIR = Path('data/chroma_db')
GRAPH_PATH = Path('data/metakgp_graph.gpickle')
COLLECTION_NAME = 'metakgp_wiki'
EMBEDDING_MODEL = 'all-MiniLM-L6-v2'


class GraphRAGRetriever:
    def __init__(self):
        print(f"[Retriever] Loading embedding model ({EMBEDDING_MODEL})...")
        self.model = SentenceTransformer(EMBEDDING_MODEL)
        
        print(f"[Retriever] Connecting to ChromaDB...")
        self.client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
        self.collection = self.client.get_collection(name=COLLECTION_NAME)
        
        print(f"[Retriever] Loading Knowledge Graph...")
        with open(GRAPH_PATH, 'rb') as f:
            self.graph = pickle.load(f)

    def search(self, query: str, top_k: int = 3, expand_graph: bool = True):
        print(f"\n[Retriever] Query: '{query}'")
        
        # 1. Vector Search
        query_embedding = self.model.encode(query).tolist()
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )
        
        if not results['ids'][0]:
            print("No results found in Vector DB.")
            return

        print("\n--- [Phase 1] Vector Search Results ---")
        
        primary_urls = set()
        
        for i in range(len(results['ids'][0])):
            distance = results['distances'][0][i]
            metadata = results['metadatas'][0][i]
            url = metadata.get('url')
            
            print(f"  [{i+1}] {metadata.get('title')} (Score: {distance:.4f})")
            if url:
                primary_urls.add(url)

        if not expand_graph:
            return

        # 2. Graph Expansion
        print("\n--- [Phase 2] Graph Expansion Neighbors ---")
        expanded_urls = set()
        
        for url in primary_urls:
            if not self.graph.has_node(url):
                continue
                
            # Find neighbors (both outgoing and incoming edges if possible)
            neighbors = list(self.graph.successors(url)) + list(self.graph.predecessors(url))
            
            for neighbor in neighbors:
                if neighbor in primary_urls or neighbor in expanded_urls:
                    continue
                    
                # Skip category nodes for retrieval context
                if self.graph.nodes[neighbor].get('type') == 'category':
                    continue
                    
                expanded_urls.add(neighbor)
                title = self.graph.nodes[neighbor].get('title', neighbor)
                print(f"  (+) Discovered linked context: {title}")

        # 3. Fetch text for expanded nodes
        # In a full pipeline, we would fetch the text for these expanded_urls and feed them to the LLM.
        print(f"\n[Summary] Retrieved {len(primary_urls)} primary chunks and {len(expanded_urls)} related pages via Graph.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='GraphRAG Retriever for MetaKGP.')
    parser.add_argument('query', type=str, help='The search query')
    parser.add_argument('--k', type=int, default=3, help='Number of vector results to return')
    parser.add_argument('--no-graph', action='store_true', help='Disable graph expansion')
    
    args = parser.parse_args()
    
    if not CHROMA_DB_DIR.exists() or not GRAPH_PATH.exists():
        print("Error: Ensure data/chroma_db and data/metakgp_graph.gpickle exist.")
        exit(1)
        
    retriever = GraphRAGRetriever()
    retriever.search(args.query, top_k=args.k, expand_graph=not args.no_graph)
