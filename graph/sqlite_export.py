import sqlite3
import networkx as nx


def export_to_sqlite(graph: nx.DiGraph, db_path: str = "data/graph.db"):
    """
    Optional debug/demo mirror of the KG. Not used at runtime by the
    app — purely so you (or a judge) can run SQL queries like:
        SELECT * FROM edges WHERE edge_type = 'MENTIONS';
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.executescript("""
        DROP TABLE IF EXISTS pages;
        DROP TABLE IF EXISTS edges;
        CREATE TABLE pages (
            url TEXT PRIMARY KEY, title TEXT, categories TEXT,
            in_degree INTEGER, out_degree INTEGER
        );
        CREATE TABLE edges (
            source TEXT, target TEXT, edge_type TEXT, category TEXT
        );
    """)

    for url, data in graph.nodes(data=True):
        cur.execute(
            "INSERT INTO pages VALUES (?, ?, ?, ?, ?)",
            (url, data.get("title", ""), ",".join(data.get("categories", [])),
             graph.in_degree(url), graph.out_degree(url)),
        )

    for u, v, data in graph.edges(data=True):
        cur.execute(
            "INSERT INTO edges VALUES (?, ?, ?, ?)",
            (u, v, data.get("edge_type", ""), data.get("category", "")),
        )

    conn.commit()
    conn.close()
    print(f"[SQLite Export] Wrote {graph.number_of_nodes()} pages, "
          f"{graph.number_of_edges()} edges to {db_path}")