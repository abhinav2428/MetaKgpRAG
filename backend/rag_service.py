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
        from langchain_groq import ChatGroq
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

        api_key = os.getenv("GROQ_API_KEY")
        llm = ChatGroq(
            model="openai/gpt-oss-20b",
            temperature=0.0,
            api_key=api_key,
        )
        self._llm = llm
        self._agent = create_react_agent(
            llm,
            tools=[search_knowledge_base],
            prompt=(
                "You are GraphMind, an AI assistant specialising in MetaKGP and "
                "IIT Kharagpur. Answer questions using the search_knowledge_base tool. "
                "Provide detailed, comprehensive, and well-explained answers."
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
        max_retries: int = 2,
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
        try:
            for attempt in range(max_retries):
                final_state = self._agent.invoke({"messages": current_messages})
                raw_content = final_state["messages"][-1].content
                if isinstance(raw_content, list):
                    last_answer = "\n".join(
                        block.get("text", "") for block in raw_content if isinstance(block, dict) and block.get("type") == "text"
                    )
                else:
                    last_answer = str(raw_content)

                # Extract tool context for MoE verification
                contexts = []
                for m in final_state["messages"]:
                    if getattr(m, "name", "") == "search_knowledge_base":
                        c = m.content
                        if isinstance(c, list):
                            c = "\n".join(b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text")
                        contexts.append(str(c))
                
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
        except Exception as e:
            print(f"[RAGService] Error during chat: {e}")
            if not last_answer:
                last_answer = (
                    "I'm sorry, I encountered an error while processing your question. "
                    "Please try again in a moment."
                )

        return last_answer


# Expose a module-level singleton
rag_service = RAGService()
