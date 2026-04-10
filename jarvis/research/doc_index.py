"""Local document indexing with ChromaDB + sentence-transformers."""

from __future__ import annotations

import hashlib
from pathlib import Path

from rich.console import Console
from rich.progress import track

from ..config import ResearchConfig
from ..utils.text import chunk_text, extract_text

_COLLECTION_NAME = "jarvis_docs"


class DocumentIndex:
    def __init__(self, cfg: ResearchConfig):
        self.cfg = cfg
        self._client = None
        self._collection = None
        self._embedder = None

    def _get_client(self):
        if self._client is None:
            import chromadb
            db_path = self.cfg.documents_dir.parent / "chroma_db"
            db_path.mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(path=str(db_path))
        return self._client

    def _get_collection(self):
        if self._collection is None:
            self._collection = self._get_client().get_or_create_collection(
                name=_COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    def _get_embedder(self):
        if self._embedder is None:
            from sentence_transformers import SentenceTransformer
            self._embedder = SentenceTransformer(self.cfg.embedding_model)
        return self._embedder

    def _file_hash(self, path: Path) -> str:
        stat = path.stat()
        return hashlib.md5(f"{path}:{stat.st_mtime}:{stat.st_size}".encode()).hexdigest()

    def index_documents(self, console: Console) -> int:
        """Index all documents in the configured directory. Returns count of new docs indexed."""
        docs_dir = self.cfg.documents_dir
        if not docs_dir.exists():
            console.print(f"[yellow]Documents directory not found: {docs_dir}[/yellow]")
            return 0

        files = [
            f for f in docs_dir.rglob("*")
            if f.is_file() and f.suffix.lower() in (".pdf", ".txt", ".md", ".rst", ".org")
        ]

        if not files:
            console.print("[yellow]No documents found to index.[/yellow]")
            return 0

        collection = self._get_collection()
        embedder = self._get_embedder()

        # Check which files need re-indexing
        existing = set()
        try:
            result = collection.get(include=["metadatas"])
            for meta in result["metadatas"]:
                if meta and "file_hash" in meta:
                    existing.add(meta["file_hash"])
        except Exception:
            pass

        indexed = 0
        for filepath in track(files, description="Indexing documents...", console=console):
            file_hash = self._file_hash(filepath)
            if file_hash in existing:
                continue

            text = extract_text(filepath)
            if not text.strip():
                continue

            chunks = chunk_text(text)
            if not chunks:
                continue

            embeddings = embedder.encode(chunks).tolist()

            ids = [f"{file_hash}_{i}" for i in range(len(chunks))]
            metadatas = [
                {
                    "source": str(filepath.relative_to(docs_dir)),
                    "file_hash": file_hash,
                    "chunk_index": i,
                }
                for i in range(len(chunks))
            ]

            collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=chunks,
                metadatas=metadatas,
            )
            indexed += 1

        console.print(f"[green]Indexed {indexed} new document(s). Total chunks in DB: {collection.count()}[/green]")
        return indexed

    def query(self, question: str, top_k: int | None = None) -> list[dict]:
        """Query the index and return relevant chunks with metadata."""
        top_k = top_k or self.cfg.top_k
        collection = self._get_collection()
        if collection.count() == 0:
            return []

        embedder = self._get_embedder()
        query_embedding = embedder.encode([question]).tolist()

        results = collection.query(
            query_embeddings=query_embedding,
            n_results=min(top_k, collection.count()),
            include=["documents", "metadatas", "distances"],
        )

        hits = []
        for i in range(len(results["ids"][0])):
            hits.append({
                "text": results["documents"][0][i],
                "source": results["metadatas"][0][i].get("source", "unknown"),
                "distance": results["distances"][0][i],
            })
        return hits
