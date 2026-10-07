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

# Resolve paths relative to the REPO ROOT (two levels up from this file)
_REPO_ROOT = Path(__file__).resolve().parent.parent
CHROMA_DB_DIR = _REPO_ROOT / 'data' / 'chroma_db'
GRAPH_PATH = _REPO_ROOT / 'data' / 'metakgp_graph.gpickle'
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

    def search_for_agent(self, query: str, top_k: int = 3) -> str:
        """
        Production search used by the LangChain agent.
        Phase 1: Vector search — finds the top_k most semantically similar chunks.
        Phase 2: Graph expansion — finds neighbors of those results in the Knowledge Graph
                 and fetches their text from ChromaDB too, giving the LLM richer context.
        """
        # ── Phase 1: Vector Search ─────────────────────────────────────────────
        query_embedding = self.model.encode(query).tolist()
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=['metadatas', 'documents', 'distances']
        )

        if not results['ids'][0]:
            return "No results found."

        context = []
        primary_urls = set()

        for i in range(len(results['ids'][0])):
            metadata = results['metadatas'][0][i]
            document = results['documents'][0][i]
            title = metadata.get('title', 'Unknown')
            url = metadata.get('url', '')

            context.append(f"Source: {title} ({url})\nContent: {document}\n")
            if url:
                primary_urls.add(url)

        # ── Phase 2: Graph Expansion ───────────────────────────────────────────
        # For each URL found in Phase 1, find its neighbours in the Knowledge Graph.
        # Then fetch those neighbour pages from ChromaDB (if indexed) and append them.
        expanded_urls = set()
        for url in primary_urls:
            if not self.graph.has_node(url):
                continue

            # Walk both outgoing (successors) and incoming (predecessors) edges
            neighbors = list(self.graph.successors(url)) + list(self.graph.predecessors(url))
            for neighbor in neighbors:
                # Skip already-seen URLs and pure category nodes
                if neighbor in primary_urls or neighbor in expanded_urls:
                    continue
                if self.graph.nodes[neighbor].get('type') == 'category':
                    continue
                expanded_urls.add(neighbor)

        # Fetch text for expanded neighbour nodes from ChromaDB (up to 5 neighbours)
        if expanded_urls:
            try:
                neighbor_results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=min(5, len(expanded_urls)),
                    where={"url": {"$in": list(expanded_urls)}},
                    include=['metadatas', 'documents']
                )
                for i in range(len(neighbor_results['ids'][0])):
                    metadata = neighbor_results['metadatas'][0][i]
                    document = neighbor_results['documents'][0][i]
                    title = metadata.get('title', 'Unknown')
                    url = metadata.get('url', '')
                    context.append(
                        f"[Graph-Expanded] Source: {title} ({url})\nContent: {document}\n"
                    )
            except Exception as e:
                # Graph expansion is best-effort; don't crash the whole query
                print(f"[Retriever] Graph expansion fetch skipped: {e}")

        return "\n---\n".join(context)


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
