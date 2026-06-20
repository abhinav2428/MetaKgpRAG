from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    openai_api_key: str = ""

    # Paths
    raw_data_dir: str = "data/raw"
    clean_data_dir: str = "data/cleaned"
    chroma_persist_dir: str = "data/chroma_db"
    graph_path: str = "data/graph.pkl"
    graphml_path: str = "data/graph.graphml"          # NEW
    sqlite_db_path: str = "data/graph.db"              # NEW
    thought_log_dir: str = "data/thought_logs"          # NEW

    # Embedding + LLM
    embedding_model: str = "all-MiniLM-L6-v2"
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.0

    # Chunking
    chunk_size: int = 512
    chunk_overlap: int = 50

    # Retrieval
    top_k_results: int = 6

    # Scraping
    scrape_delay_seconds: float = 0.5
    max_pages: int = 2000

    # GoT / MoE scoring                                  # NEW BLOCK
    score_threshold: float = 0.5
    weight_source: float = 0.4
    weight_hallucination: float = 0.4
    weight_logic: float = 0.2
    max_kg_expansions_per_seed: int = 3
    max_kg_expansions_total: int = 8

    class Config:
        env_file = ".env"
        extra = "ignore"   # silently skip any .env keys not declared above

settings = Settings()