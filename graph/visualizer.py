import networkx as nx
from pyvis.network import Network
from typing import List


class GraphVisualizer:
    """
    Renders an interactive subgraph around query-relevant pages
    as a self-contained HTML string (for Streamlit embedding).
    """

    def __init__(self, graph: nx.DiGraph):
        self.graph = graph

    def render_subgraph(
        self,
        highlight_urls: List[str],
        hop_depth: int = 1,
    ) -> str:
        if not highlight_urls:
            return "<p style='color:grey'>No graph data for this query.</p>"

        # Collect nodes: highlighted + 1-hop neighbors
        nodes_to_show = set()
        for url in highlight_urls:
            if url in self.graph:
                nodes_to_show.add(url)
                for nb in self.graph.successors(url):
                    nodes_to_show.add(nb)
                for nb in self.graph.predecessors(url):
                    nodes_to_show.add(nb)

        # Cap size for performance
        if len(nodes_to_show) > 60:
            # Keep only highlighted + their direct neighbors
            nodes_to_show = set(highlight_urls) | set(
                nb
                for url in highlight_urls if url in self.graph
                for nb in list(self.graph.successors(url))[:5]
            )

        subgraph = self.graph.subgraph(nodes_to_show)

        net = Network(
            height="460px",
            width="100%",
            bgcolor="#0e1117",
            font_color="#ffffff",
            directed=True,
        )

        for node_id, data in subgraph.nodes(data=True):
            is_highlight = node_id in highlight_urls
            label = data.get("title", node_id.split("/")[-1])[:30]
            net.add_node(
                node_id,
                label=label,
                title=f"{data.get('title', '')}\n{node_id}",
                color="#ff4b4b" if is_highlight else "#4b9eff",
                size=25 if is_highlight else 12,
                borderWidth=3 if is_highlight else 1,
            )

        for src, dst in subgraph.edges():
            net.add_edge(src, dst, color="#555555", width=1)

        net.set_options("""
        {
          "physics": {
            "forceAtlas2Based": {
              "gravitationalConstant": -50,
              "springLength": 100
            },
            "solver": "forceAtlas2Based",
            "stabilization": {"iterations": 100}
          }
        }
        """)

        return net.generate_html(notebook=False)


# ── Thought Graph renderer (module-level) ──────────────────────────────────

OP_COLORS = {
    "SEED": "#4b9eff",
    "EXPAND": "#7f77dd",
    "GENERATE": "#f0997b",
    "REFINE": "#ef9f27",
    "AGGREGATE": "#5dcaa5",
}


def render_thought_graph(tg_dict: dict) -> str:
    """
    Renders the per-query ThoughtGraph.to_dict() output as an
    interactive pyvis HTML graph — shown alongside the KG subgraph
    so judges can see both the static structure and the live reasoning.
    """
    net = Network(height="420px", width="100%", bgcolor="#0e1117",
                  font_color="#ffffff", directed=True)

    for node in tg_dict["nodes"]:
        is_pruned = node["status"] == "PRUNED"
        score_label = f"{node['score']:.2f}" if node["score"] is not None else "—"
        net.add_node(
            node["thought_id"],
            label=f"{node['operation']}\n({score_label})",
            title=node["content"][:200],
            color=OP_COLORS.get(node["operation"], "#888"),
            shape="dot" if not is_pruned else "diamond",
            size=28 if node["status"] == "FINAL" else 16,
            borderWidth=4 if node["status"] == "FINAL" else 1,
            opacity=0.35 if is_pruned else 1.0,
        )

    for edge in tg_dict["edges"]:
        net.add_edge(edge["source"], edge["target"], label=edge["relation"], color="#555555")

    return net.generate_html(notebook=False)