"""
Database Manager Module – Vector DB Explorer
Provides comprehensive CRUD operations for ChromaDB collections.
Covers all Milestone 5 requirements: create, update, retrieve, delete, insert, query.
"""

import logging
import time
from typing import Dict, List, Optional, Any

import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)


class ChromaDBManager:
    """
    Manages ChromaDB collections and documents.
    Provides full CRUD + similarity search operations.
    """

    def __init__(self, persist_directory: str = "./chroma_explorer_db"):
        """
        Initialize the ChromaDB manager.

        Args:
            persist_directory: Directory for Chroma persistence.
        """
        self.persist_directory = persist_directory
        try:
            self.client = chromadb.PersistentClient(
                path=persist_directory,
                settings=Settings(anonymized_telemetry=False)
            )
        except AttributeError:
            # Very old chromadb versions (<0.4) without PersistentClient
            self.client = chromadb.Client(Settings(
                persist_directory=persist_directory,
                anonymized_telemetry=False
            ))
        logger.info(f"ChromaDB manager initialized (persist_dir={persist_directory})")

    # ─── Collection Operations ───

    def create_collection(self, name: str, metadata: Optional[Dict] = None) -> Dict:
        """
        Create a new collection.

        Args:
            name: Collection name (alphanumeric + underscores).
            metadata: Optional metadata for the collection.

        Returns:
            Dictionary with collection info.
        """
        try:
            meta = metadata or {"hnsw:space": "cosine"}
            collection = self.client.create_collection(name=name, metadata=meta)
            logger.info(f"Created collection: {name}")
            return {
                "name": collection.name,
                "metadata": collection.metadata,
                "count": collection.count(),
                "status": "created"
            }
        except Exception as e:
            if "already exists" in str(e).lower():
                raise ValueError(f"Collection '{name}' already exists.")
            raise

    def list_collections(self) -> List[Dict]:
        """
        List all collections.

        Returns:
            List of collection info dictionaries.
        """
        collections = self.client.list_collections()
        result = []
        for col in collections:
            # chromadb>=0.6 returns names (str); older versions return objects
            if isinstance(col, str):
                col = self.client.get_collection(name=col)
            result.append({
                "name": col.name,
                "metadata": col.metadata,
                "count": col.count()
            })
        return result

    def get_collection(self, name: str):
        """
        Get a collection by name.

        Args:
            name: Collection name.

        Returns:
            ChromaDB Collection object.
        """
        return self.client.get_collection(name=name)

    def delete_collection(self, name: str) -> Dict:
        """
        Delete a collection.

        Args:
            name: Collection name.

        Returns:
            Confirmation dictionary.
        """
        self.client.delete_collection(name=name)
        logger.info(f"Deleted collection: {name}")
        return {"name": name, "status": "deleted"}

    # ─── Document Operations ───

    def insert_documents(
        self,
        collection_name: str,
        documents: List[str],
        ids: Optional[List[str]] = None,
        embeddings: Optional[List[List[float]]] = None,
        metadatas: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Insert documents into a collection.

        Args:
            collection_name: Target collection name.
            documents: List of text documents.
            ids: Optional document IDs (auto-generated if not provided).
            embeddings: Optional pre-computed embeddings.
            metadatas: Optional metadata for each document.

        Returns:
            Insert result with count.
        """
        collection = self.get_collection(collection_name)

        if ids is None:
            timestamp = int(time.time() * 1000)
            ids = [f"doc_{timestamp}_{i}" for i in range(len(documents))]

        kwargs = {
            "ids": ids,
            "documents": documents,
        }

        if embeddings:
            kwargs["embeddings"] = embeddings
        if metadatas:
            kwargs["metadatas"] = metadatas
        else:
            kwargs["metadatas"] = [{"inserted_at": time.time()} for _ in documents]

        collection.add(**kwargs)
        logger.info(f"Inserted {len(documents)} documents into '{collection_name}'")

        return {
            "collection": collection_name,
            "inserted_count": len(documents),
            "ids": ids,
            "status": "inserted"
        }

    def get_documents(
        self,
        collection_name: str,
        ids: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict:
        """
        Retrieve documents from a collection.

        Args:
            collection_name: Collection name.
            ids: Optional specific document IDs to retrieve.
            limit: Maximum documents to return.
            offset: Pagination offset.

        Returns:
            Dictionary with documents and metadata.
        """
        collection = self.get_collection(collection_name)

        if ids:
            results = collection.get(
                ids=ids,
                include=["documents", "metadatas", "embeddings"]
            )
        else:
            results = collection.get(
                limit=limit,
                offset=offset,
                include=["documents", "metadatas", "embeddings"]
            )

        documents = []
        if results and results["ids"]:
            docs = results.get("documents")
            metas = results.get("metadatas")
            embs = results.get("embeddings")
            for i, doc_id in enumerate(results["ids"]):
                doc = {
                    "id": doc_id,
                    "document": docs[i] if docs is not None else None,
                    "metadata": (metas[i] if metas is not None else None) or {},
                }
                # Include embedding dimension but not full vector (too large).
                # Note: embeddings may be a numpy array, so avoid truthiness checks.
                if embs is not None and len(embs) > i and embs[i] is not None:
                    doc["embedding_dim"] = len(embs[i])
                documents.append(doc)

        return {
            "collection": collection_name,
            "total": collection.count(),
            "returned": len(documents),
            "documents": documents
        }

    def update_document(
        self,
        collection_name: str,
        doc_id: str,
        document: Optional[str] = None,
        metadata: Optional[Dict] = None,
        embedding: Optional[List[float]] = None
    ) -> Dict:
        """
        Update a document in a collection.

        Args:
            collection_name: Collection name.
            doc_id: Document ID to update.
            document: New document text.
            metadata: New metadata.
            embedding: New embedding.

        Returns:
            Update confirmation.
        """
        collection = self.get_collection(collection_name)

        kwargs = {"ids": [doc_id]}
        if document is not None:
            kwargs["documents"] = [document]
        if metadata is not None:
            metadata["updated_at"] = time.time()
            kwargs["metadatas"] = [metadata]
        if embedding is not None:
            kwargs["embeddings"] = [embedding]

        collection.update(**kwargs)
        logger.info(f"Updated document '{doc_id}' in '{collection_name}'")

        return {
            "collection": collection_name,
            "id": doc_id,
            "status": "updated"
        }

    def delete_document(self, collection_name: str, doc_id: str) -> Dict:
        """
        Delete a document from a collection.

        Args:
            collection_name: Collection name.
            doc_id: Document ID to delete.

        Returns:
            Deletion confirmation.
        """
        collection = self.get_collection(collection_name)
        collection.delete(ids=[doc_id])
        logger.info(f"Deleted document '{doc_id}' from '{collection_name}'")

        return {
            "collection": collection_name,
            "id": doc_id,
            "status": "deleted"
        }

    # ─── Search Operations ───

    def similarity_search(
        self,
        collection_name: str,
        query_text: Optional[str] = None,
        query_embedding: Optional[List[float]] = None,
        top_k: int = 5
    ) -> Dict:
        """
        Perform vector similarity search.

        Args:
            collection_name: Collection name.
            query_text: Text query (uses Chroma's internal embedding).
            query_embedding: Pre-computed query embedding.
            top_k: Number of results to return.

        Returns:
            Search results with scores.
        """
        collection = self.get_collection(collection_name)
        start_time = time.time()

        count = collection.count()
        top_k = max(1, int(top_k))
        if count == 0:
            return {
                "collection": collection_name,
                "query": query_text,
                "top_k": top_k,
                "results_count": 0,
                "search_time_seconds": 0.0,
                "results": []
            }
        n_results = min(top_k, count)

        if query_embedding is not None:
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                include=["documents", "metadatas", "distances"]
            )
        elif query_text:
            results = collection.query(
                query_texts=[query_text],
                n_results=n_results,
                include=["documents", "metadatas", "distances"]
            )
        else:
            raise ValueError("Either query_text or query_embedding must be provided.")

        search_time = round(time.time() - start_time, 4)

        formatted = []
        if results and results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                formatted.append({
                    "id": doc_id,
                    "document": results["documents"][0][i] if results["documents"] else None,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else None,
                    "similarity": round(1.0 - results["distances"][0][i], 4) if results["distances"] else None
                })

        return {
            "collection": collection_name,
            "query": query_text,
            "top_k": top_k,
            "results_count": len(formatted),
            "search_time_seconds": search_time,
            "results": formatted
        }

    # ─── Statistics ───

    def get_collection_stats(self, collection_name: str) -> Dict:
        """
        Get detailed statistics for a collection.

        Args:
            collection_name: Collection name.

        Returns:
            Statistics dictionary.
        """
        collection = self.get_collection(collection_name)
        count = collection.count()

        stats = {
            "name": collection_name,
            "metadata": collection.metadata,
            "document_count": count,
        }

        if count > 0:
            # Sample first few docs for stats
            sample = collection.get(limit=min(count, 10), include=["documents", "metadatas"])
            if sample["documents"]:
                doc_lengths = [len(d) for d in sample["documents"] if d]
                stats["sample_avg_doc_length"] = round(sum(doc_lengths) / len(doc_lengths)) if doc_lengths else 0

        return stats
