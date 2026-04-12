"""
LlamaIndex RAG pipeline for semantic search with LLM-augmented answers.
"""
import logging
from typing import Optional

from llama_index.core import Settings as LlamaSettings
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core import VectorStoreIndex, StorageContext

from config import settings
from intelligence.vectorstore import get_collection

logger = logging.getLogger("ghostexodus.rag")

_index = None


def _configure_llama():
    LlamaSettings.llm = Ollama(
        model=settings.LLM_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
        request_timeout=120.0,
        context_window=settings.LLM_CONTEXT_WINDOW,
    )
    LlamaSettings.embed_model = OllamaEmbedding(
        model_name=settings.EMBED_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
    )


def get_rag_index():
    global _index
    if _index is None:
        _configure_llama()
        collection = get_collection()
        vector_store = ChromaVectorStore(chroma_collection=collection)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        _index = VectorStoreIndex.from_vector_store(
            vector_store, storage_context=storage_context
        )
    return _index


async def rag_query(question: str, top_k: int = 10) -> dict:
    """
    Run a RAG query: retrieve relevant messages then synthesize an LLM answer.
    Returns {answer, sources}.
    """
    try:
        index = get_rag_index()
        query_engine = index.as_query_engine(
            similarity_top_k=top_k,
            streaming=False,
        )
        response = query_engine.query(question)
        sources = []
        if hasattr(response, "source_nodes"):
            for node in response.source_nodes:
                sources.append({
                    "content": node.node.text[:300],
                    "metadata": node.node.metadata,
                    "score": round(node.score or 0.0, 4),
                })
        return {
            "answer": str(response),
            "sources": sources,
        }
    except Exception as e:
        logger.error(f"RAG query failed: {e}")
        return {"answer": f"Query failed: {str(e)}", "sources": []}
