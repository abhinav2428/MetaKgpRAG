"""
backend/rag_service.py
----------------------
A singleton wrapper around the GraphRAG agent that is safe to import
into FastAPI (avoids re-loading models on every request).

The agent is initialised lazily on the first call so the API server can
start quickly even if the ChromaDB / graph files are large.
"""

import sys
import os
from pathlib import Path
from typing import Optional

# ── Make sure the repo root is importable ────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Fix Windows console encoding issues for Unicode characters
if hasattr(sys.stdout, "reconfigure") and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")


class RAGService:
    """Lazy-initialised singleton for the LangGraph RAG agent."""

    _instance: Optional["RAGService"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def _initialize(self):
        if self._initialized:
            return
        print("[RAGService] Loading GraphRAG components…")
        from langchain_google_genai import ChatGoogleGenerativeAI
        from langgraph.prebuilt import create_react_agent
        from langchain_core.tools import tool
        from rag.retriever import GraphRAGRetriever
        from rag.agent import MoEVerification, run_moe_verification

        self._retriever = GraphRAGRetriever()
        self._run_moe = run_moe_verification

        @tool
        def search_knowledge_base(query: str) -> str:
            """Useful for when you need to answer questions about MetaKGP, IIT Kharagpur,
            halls, courses, and related entities. Input should be a specific search query."""
            return self._retriever.search_for_agent(query, top_k=10)

        api_key = os.getenv("GOOGLE_API_KEY")
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0.0,
            google_api_key=api_key,
        )
        self._llm = llm
        self._agent = create_react_agent(
            llm,
            tools=[search_knowledge_base],
            prompt=(
                "You are GraphMind, an AI assistant specialising in MetaKGP and "
                "IIT Kharagpur. Answer questions using the search_knowledge_base tool. "
                "Be concise and accurate."
            ),
        )
        self._MoEVerification = MoEVerification
        self._initialized = True
        print("[RAGService] Ready.")

    # ── Public API ────────────────────────────────────────────────────────────

    def chat(
        self,
        user_message: str,
        history: list[tuple[str, str]],
        max_retries: int = 3,
    ) -> str:
        """
        Run one turn of the conversation.

        Args:
            user_message: The latest user query.
            history: List of (role, content) tuples for prior turns.
                     role is "user" or "assistant".
            max_retries: MoE self-correction retries.

        Returns:
            The final (verified) AI answer as a string.
        """
        self._initialize()

        # Build message list in LangGraph format (tuples of role, content)
        current_messages = list(history) + [("user", user_message)]

        last_answer = ""
        for attempt in range(max_retries):
            final_state = self._agent.invoke({"messages": current_messages})
            last_answer = final_state["messages"][-1].content

            # Extract tool context for MoE verification
            contexts = [
                str(m.content)
                for m in final_state["messages"]
                if getattr(m, "name", "") == "search_knowledge_base"
            ]
            combined_context = "\n\n".join(contexts) or "No context retrieved."

            verification = self._run_moe(
                self._llm, user_message, combined_context, last_answer
            )

            if verification.is_valid:
                break
            elif attempt < max_retries - 1:
                current_messages = final_state["messages"]
                current_messages.append((
                    "user",
                    f"Your previous answer failed verification.\n"
                    f"Feedback: {verification.feedback}\n"
                    "Please revise your answer. Do NOT hallucinate.",
                ))

        return last_answer


# Expose a module-level singleton
rag_service = RAGService()
