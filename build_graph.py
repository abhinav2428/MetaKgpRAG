#!/usr/bin/env python3
"""Build the KG: LINKS_TO + SAME_CATEGORY + MENTIONS edges, then export."""
import json
from pathlib import Path
from graph.got_builder import GoTBuilder
from graph.sqlite_export import export_to_sqlite
from config.settings import settings

if __name__ == "__main__":
    builder = GoTBuilder()

    print("=== Pass 1: LINKS_TO (explicit wikilinks) ===")
    builder.build()

    print("\n=== Pass 2: SAME_CATEGORY ===")
    builder.add_category_edges()

    print("\n=== Pass 3: MENTIONS ===")
    full_texts = {}
    for fp in Path(settings.clean_data_dir).glob("*.json"):
        with open(fp, encoding="utf-8") as f:
            page = json.load(f)
        full_texts[page["url"]] = page["text"]
    builder.add_mention_edges(full_texts)

    builder.save()
    builder.export_graphml()
    export_to_sqlite(builder.graph, settings.sqlite_db_path)

    print(
        f"\n✅ Final graph: {builder.graph.number_of_nodes()} nodes, "
        f"{builder.graph.number_of_edges()} edges "
        f"(LINKS_TO + SAME_CATEGORY + MENTIONS combined)."
    )