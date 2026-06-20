import json
import pickle
import os
from pathlib import Path
from typing import Optional
import networkx as nx
from config.settings import settings
from collections import defaultdict


class GoTBuilder:
    """
    Builds a directed graph where:
      Nodes = wiki pages (keyed by URL)
      Edges = hyperlinks between pages (LINKS_TO)
      Node attrs = title, categories, short text snippet
    """

    def __init__(self):
        self.graph = nx.DiGraph()

    def build(self, clean_dir: str = None) -> nx.DiGraph:
        clean_dir = clean_dir or settings.clean_data_dir
        files = list(Path(clean_dir).glob("*.json"))
        print(f"[GoT Builder] Building graph from {len(files)} pages...")

        # Pass 1: add all nodes
        url_to_data = {}
        for fp in files:
            with open(fp, encoding="utf-8") as f:
                page = json.load(f)
            self.graph.add_node(
                page["url"],
                title=page["title"],
                snippet=page["text"][:300],
                categories=page.get("categories", []),
            )
            url_to_data[page["url"]] = page

        # Pass 2: add edges (only between pages we have)
        known_urls = set(url_to_data.keys())
        edges_added = 0
        for url, page in url_to_data.items():
            for linked_url in page.get("links", []):
                if linked_url in known_urls and linked_url != url:
                    self.graph.add_edge(
                        url,
                        linked_url,
                        edge_type="LINKS_TO",
                    )
                    edges_added += 1

        print(
            f"[GoT Builder] Graph: {self.graph.number_of_nodes()} nodes, "
            f"{edges_added} edges."
        )
        return self.graph

    def save(self, path: str = None):
        path = path or settings.graph_path
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self.graph, f)
        print(f"[GoT Builder] Graph saved to {path}")

    def load(self, path: str = None) -> nx.DiGraph:
        path = path or settings.graph_path
        with open(path, "rb") as f:
            self.graph = pickle.load(f)
        print(
            f"[GoT Builder] Loaded graph: "
            f"{self.graph.number_of_nodes()} nodes, "
            f"{self.graph.number_of_edges()} edges."
        )
        return self.graph



    def add_category_edges(self, max_cluster_size: int = 50):
        """
        Connects pages sharing a MediaWiki category but lacking a
        direct hyperlink — e.g. all 'Society' or 'Hall' pages.
        """
        cat_to_pages = defaultdict(list)
        for url, data in self.graph.nodes(data=True):
            for cat in data.get("categories", []):
                cat_to_pages[cat].append(url)

        added = 0
        for cat, pages in cat_to_pages.items():
            if len(pages) < 2 or len(pages) > max_cluster_size:
                continue
            for i, a in enumerate(pages):
                for b in pages[i + 1:]:
                    self.graph.add_edge(a, b, edge_type="SAME_CATEGORY", category=cat)
                    self.graph.add_edge(b, a, edge_type="SAME_CATEGORY", category=cat)
                    added += 2
        print(f"[GoT Builder] Added {added} SAME_CATEGORY edges.")

    def add_mention_edges(self, full_texts: dict):
        """
        Catches informal cross-references in prose that were never
        captured as wikilinks. `full_texts` = {url: full_cleaned_text},
        read fresh from data/cleaned/ (NOT the 300-char node snippet).
        """
        titles_to_url = {
            data["title"].lower(): url
            for url, data in self.graph.nodes(data=True)
            if len(data["title"]) > 4
        }

        added = 0
        for url, text in full_texts.items():
            text_lower = text.lower()
            for title_lower, target_url in titles_to_url.items():
                if target_url == url:
                    continue
                if title_lower in text_lower and not self.graph.has_edge(url, target_url):
                    self.graph.add_edge(url, target_url, edge_type="MENTIONS", weight=0.5)
                    added += 1
        print(f"[GoT Builder] Added {added} MENTIONS edges.")

    def export_graphml(self, path: str = None):
        """Human-inspectable export for Gephi / demo purposes."""
        path = path or settings.graphml_path
        g2 = self.graph.copy()
        for _, data in g2.nodes(data=True):
            if isinstance(data.get("categories"), list):
                data["categories"] = ",".join(data["categories"])
        nx.write_graphml(g2, path)
        print(f"[GoT Builder] GraphML exported to {path}")