"""
rag/graph_builder.py
--------------------
Builds a NetworkX Knowledge Graph from the processed MetaKGP JSON files.
Nodes are wiki pages (identified by URL) and categories.
Edges are hyperlinks and category memberships.
"""

import json
import os
import pickle
import networkx as nx
from pathlib import Path
from tqdm import tqdm

PROCESSED_DIR = Path('data/processed')
GRAPH_OUTPUT_PATH = Path('data/metakgp_graph.gpickle')


def build_graph():
    print("[GraphBuilder] Initializing directed graph...")
    G = nx.DiGraph()
    
    files = sorted(PROCESSED_DIR.glob('*.json'))
    print(f"[GraphBuilder] Found {len(files)} processed pages.")
    
    for fpath in tqdm(files, desc="Building Graph"):
        with open(fpath, encoding='utf-8') as f:
            data = json.load(f)
            
        url = data.get('url')
        if not url:
            continue
            
        title = data.get('title', 'Unknown Title')
        page_type = data.get('page_type', 'unknown')
        
        # Add the main page node
        G.add_node(
            url, 
            title=title, 
            type=page_type, 
            url=url,
            is_page=True
        )
        
        # Add 'LINKS_TO' edges
        for link in data.get('links', []):
            if not link.startswith('http'):
                continue
            # We add the target node if it doesn't exist (it might be added properly later 
            # if we have the JSON for it, which will update its attributes).
            if not G.has_node(link):
                # Placeholder node for external or not-yet-processed links
                G.add_node(link, title=link.split('/')[-1], type='unknown', url=link, is_page=False)
                
            G.add_edge(url, link, relation='LINKS_TO')
            
        # Add 'BELONGS_TO' category edges
        for cat in data.get('categories', []):
            cat_id = f"category:{cat}"
            if not G.has_node(cat_id):
                G.add_node(cat_id, title=f"Category: {cat}", type='category', is_page=False)
                
            G.add_edge(url, cat_id, relation='BELONGS_TO')

    print(f"\n[GraphBuilder] Graph constructed!")
    print(f"  Total Nodes: {G.number_of_nodes()}")
    print(f"  Total Edges: {G.number_of_edges()}")
    
    print(f"[GraphBuilder] Saving graph to {GRAPH_OUTPUT_PATH} ...")
    with open(GRAPH_OUTPUT_PATH, 'wb') as f:
        pickle.dump(G, f, pickle.HIGHEST_PROTOCOL)
        
    print("[GraphBuilder] Done.")


if __name__ == '__main__':
    build_graph()
