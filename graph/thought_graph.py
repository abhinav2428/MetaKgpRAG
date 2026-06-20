import uuid
import time
import json
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Callable
import networkx as nx

from config.settings import settings


class ThoughtStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PRUNED = "PRUNED"
    FINAL = "FINAL"


class Operation(str, Enum):
    SEED = "SEED"
    EXPAND = "EXPAND"
    GENERATE = "GENERATE"
    REFINE = "REFINE"
    AGGREGATE = "AGGREGATE"


@dataclass
class ThoughtNode:
    content: str
    operation: Operation
    source_urls: List[str] = field(default_factory=list)
    source_chunk_ids: List[str] = field(default_factory=list)
    parent_ids: List[str] = field(default_factory=list)
    thought_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    score: Optional[float] = None
    expert_verdicts: Dict = field(default_factory=dict)
    status: ThoughtStatus = ThoughtStatus.ACTIVE
    depth: int = 0
    created_at: float = field(default_factory=time.time)


class ThoughtGraph:
    """
    Per-query ephemeral reasoning graph. No dependency on experts/ —
    scoring is injected as a callback from the orchestrator.
    """

    def __init__(self, query: str, query_id: str = None):
        self.query = query
        self.query_id = query_id or uuid.uuid4().hex[:10]
        self.g = nx.DiGraph()

    # ── Generate ──────────────────────────────────────────────────────────

    def add_seed(self, content: str, url: str, chunk_id: str) -> ThoughtNode:
        node = ThoughtNode(
            content=content, operation=Operation.SEED,
            source_urls=[url], source_chunk_ids=[chunk_id] if chunk_id else [],
            depth=0,
        )
        self.g.add_node(node.thought_id, data=node)
        return node

    def add_expansion(self, content: str, url: str, parent: ThoughtNode) -> ThoughtNode:
        node = ThoughtNode(
            content=content, operation=Operation.EXPAND,
            source_urls=[url], parent_ids=[parent.thought_id],
            depth=parent.depth + 1,
        )
        self.g.add_node(node.thought_id, data=node)
        self.g.add_edge(parent.thought_id, node.thought_id, relation="DERIVES_FROM")
        return node

    def add_candidate(self, content: str, parents: List[ThoughtNode], method: str) -> ThoughtNode:
        node = ThoughtNode(
            content=content, operation=Operation.GENERATE,
            source_urls=list({u for p in parents for u in p.source_urls}),
            parent_ids=[p.thought_id for p in parents],
            depth=max((p.depth for p in parents), default=0) + 1,
        )
        node.expert_verdicts["method"] = method
        self.g.add_node(node.thought_id, data=node)
        for p in parents:
            self.g.add_edge(p.thought_id, node.thought_id, relation="SUPPORTS")
        return node

    # ── Score ──────────────────────────────────────────────────────────────

    def score(self, node: ThoughtNode, scorer: Callable[[ThoughtNode], Dict]) -> ThoughtNode:
        result = scorer(node)
        node.expert_verdicts.update(result["verdicts"])
        node.score = result["combined_score"]
        self.g.nodes[node.thought_id]["data"] = node
        return node

    # ── Refine ─────────────────────────────────────────────────────────────

    def refine(self, node: ThoughtNode, new_content: str) -> ThoughtNode:
        refined = ThoughtNode(
            content=new_content, operation=Operation.REFINE,
            source_urls=node.source_urls, parent_ids=[node.thought_id],
            depth=node.depth + 1,
        )
        self.g.add_node(refined.thought_id, data=refined)
        self.g.add_edge(node.thought_id, refined.thought_id, relation="REFINES")
        return refined

    # ── Aggregate ──────────────────────────────────────────────────────────

    def aggregate(self, nodes: List[ThoughtNode], merged_content: str) -> ThoughtNode:
        merged = ThoughtNode(
            content=merged_content, operation=Operation.AGGREGATE,
            source_urls=list({u for n in nodes for u in n.source_urls}),
            parent_ids=[n.thought_id for n in nodes],
            depth=max(n.depth for n in nodes) + 1,
            status=ThoughtStatus.FINAL,
        )
        self.g.add_node(merged.thought_id, data=merged)
        for n in nodes:
            self.g.add_edge(n.thought_id, merged.thought_id, relation="AGGREGATES_INTO")
        return merged

    # ── Prune ──────────────────────────────────────────────────────────────

    def prune(self, node: ThoughtNode, reason: str):
        node.status = ThoughtStatus.PRUNED
        node.expert_verdicts["prune_reason"] = reason
        self.g.nodes[node.thought_id]["data"] = node

    # ── Selection ──────────────────────────────────────────────────────────

    def best_active(self) -> Optional[ThoughtNode]:
        candidates = [
            d["data"] for _, d in self.g.nodes(data=True)
            if d["data"].status != ThoughtStatus.PRUNED and d["data"].score is not None
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda n: n.score)

    # ── Persistence ────────────────────────────────────────────────────────

    def to_dict(self) -> Dict:
        return {
            "query_id": self.query_id,
            "query": self.query,
            "nodes": [
                {
                    "thought_id": d["data"].thought_id,
                    "content": d["data"].content[:500],
                    "operation": d["data"].operation,
                    "parent_ids": d["data"].parent_ids,
                    "source_urls": d["data"].source_urls,
                    "score": d["data"].score,
                    "status": d["data"].status,
                    "depth": d["data"].depth,
                    "expert_verdicts": d["data"].expert_verdicts,   # FIX: was missing before
                }
                for _, d in self.g.nodes(data=True)
            ],
            "edges": [
                {"source": u, "target": v, "relation": d.get("relation")}
                for u, v, d in self.g.edges(data=True)
            ],
        }

    def save(self, out_dir: str = None) -> str:
        out_dir = out_dir or settings.thought_log_dir   # FIX: uses settings now
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir, f"{self.query_id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        return path