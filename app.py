"""
app.py – Vector DB Explorer Flask Application
RTB Cycle 16 – Generative AI Advance (Milestone 5)

A Vector Database Management UI providing RESTful endpoints
for all CRUD operations and similarity search on ChromaDB.
"""

import os
import logging
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

from src.db_manager import ChromaDBManager
from src.chunking import chunk_text, get_chunking_stats
from src.embeddings import (
    generate_embeddings,
    generate_single_embedding,
    get_embedding_info,
    compute_similarity_matrix,
    reduce_dimensions
)

# ─── Configuration ───

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)  # silence model-download chatter

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")

# Initialize database manager (path anchored to this file so cwd doesn't matter)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_manager = ChromaDBManager(persist_directory=os.path.join(BASE_DIR, "chroma_explorer_db"))


def _to_int(value, default, minimum=None, maximum=None):
    """Safely parse an int with optional bounds."""
    try:
        result = int(value)
    except (TypeError, ValueError):
        result = default
    if minimum is not None:
        result = max(minimum, result)
    if maximum is not None:
        result = min(maximum, result)
    return result


# ─── Page Routes ───

@app.route("/")
def index():
    """Serve the Vector DB Explorer UI."""
    return render_template("index.html")


# ─── Collection API ───

@app.route("/api/collections", methods=["GET"])
def list_collections():
    """List all collections."""
    try:
        collections = db_manager.list_collections()
        return jsonify({"collections": collections})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/collections", methods=["POST"])
def create_collection():
    """Create a new collection."""
    data = request.get_json(silent=True)
    if not data or "name" not in data:
        return jsonify({"error": "Collection name is required."}), 400

    name = data["name"].strip()
    if not name:
        return jsonify({"error": "Collection name cannot be empty."}), 400

    try:
        result = db_manager.create_collection(name=name, metadata=data.get("metadata"))
        return jsonify(result), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 409
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/collections/<name>", methods=["DELETE"])
def delete_collection(name):
    """Delete a collection."""
    try:
        result = db_manager.delete_collection(name)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/collections/<name>/stats", methods=["GET"])
def collection_stats(name):
    """Get collection statistics."""
    try:
        stats = db_manager.get_collection_stats(name)
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── Document API ───

@app.route("/api/documents", methods=["GET"])
def list_documents():
    """List documents in a collection."""
    collection = request.args.get("collection")
    if not collection:
        return jsonify({"error": "Collection name required (query param: collection)."}), 400

    limit = _to_int(request.args.get("limit"), 100, minimum=1, maximum=1000)
    offset = _to_int(request.args.get("offset"), 0, minimum=0)

    try:
        result = db_manager.get_documents(collection, limit=limit, offset=offset)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/documents", methods=["POST"])
def insert_documents():
    """Insert documents into a collection."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body is required."}), 400

    collection = data.get("collection")
    documents = data.get("documents", [])
    if isinstance(documents, str):
        documents = [documents]
    documents = [d.strip() for d in documents if isinstance(d, str) and d.strip()]

    ids = data.get("ids")
    if ids is not None:
        ids = [str(i).strip() for i in ids if str(i).strip()]
        if len(ids) != len(documents):
            ids = None  # fall back to auto-generated IDs

    if not collection:
        return jsonify({"error": "Collection name is required."}), 400
    if not documents:
        return jsonify({"error": "At least one non-empty document is required."}), 400

    try:
        # Generate embeddings for the documents
        embeddings = generate_embeddings(documents)

        result = db_manager.insert_documents(
            collection_name=collection,
            documents=documents,
            ids=ids,
            embeddings=embeddings,
            metadatas=data.get("metadatas")
        )
        return jsonify(result), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/documents/<doc_id>", methods=["PUT"])
def update_document(doc_id):
    """Update a document."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body is required."}), 400

    collection = data.get("collection")
    if not collection:
        return jsonify({"error": "Collection name is required."}), 400

    try:
        # Regenerate embedding if document text changed
        embedding = None
        if data.get("document"):
            embedding = generate_single_embedding(data["document"])

        result = db_manager.update_document(
            collection_name=collection,
            doc_id=doc_id,
            document=data.get("document"),
            metadata=data.get("metadata"),
            embedding=embedding
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/documents/<doc_id>", methods=["DELETE"])
def delete_document(doc_id):
    """Delete a document."""
    collection = request.args.get("collection")
    if not collection:
        return jsonify({"error": "Collection name required (query param: collection)."}), 400

    try:
        result = db_manager.delete_document(collection, doc_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── Search API ───

@app.route("/api/search", methods=["POST"])
def similarity_search():
    """Perform vector similarity search."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body is required."}), 400

    collection = data.get("collection")
    query = (data.get("query") or "").strip()
    top_k = _to_int(data.get("top_k"), 5, minimum=1, maximum=50)

    if not collection:
        return jsonify({"error": "Collection name is required."}), 400
    if not query:
        return jsonify({"error": "Search query is required."}), 400

    try:
        # Generate query embedding
        query_embedding = generate_single_embedding(query)

        result = db_manager.similarity_search(
            collection_name=collection,
            query_embedding=query_embedding,
            top_k=top_k
        )
        result["query"] = query
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── Chunking API ───

@app.route("/api/chunk", methods=["POST"])
def chunk_endpoint():
    """Chunk text and return the chunks with statistics."""
    data = request.get_json(silent=True)
    if not data or "text" not in data:
        return jsonify({"error": "Text content is required."}), 400

    text = data["text"]
    if not isinstance(text, str) or not text.strip():
        return jsonify({"error": "Text content cannot be empty."}), 400
    method = data.get("method", "sentence")
    kwargs = {}

    if method == "sentence":
        kwargs["sentences_per_chunk"] = _to_int(data.get("sentences_per_chunk"), 3, minimum=1)
    elif method == "character":
        kwargs["chunk_size"] = _to_int(data.get("chunk_size"), 500, minimum=10)
        kwargs["overlap"] = _to_int(data.get("overlap"), 50, minimum=0)
        if kwargs["overlap"] >= kwargs["chunk_size"]:
            kwargs["overlap"] = kwargs["chunk_size"] // 5
    elif method == "word":
        kwargs["words_per_chunk"] = _to_int(data.get("words_per_chunk"), 100, minimum=1)
        kwargs["overlap_words"] = _to_int(data.get("overlap_words"), 10, minimum=0)
        if kwargs["overlap_words"] >= kwargs["words_per_chunk"]:
            kwargs["overlap_words"] = kwargs["words_per_chunk"] // 5

    try:
        chunks = chunk_text(text, method=method, **kwargs)
        stats = get_chunking_stats(chunks)
        return jsonify({"chunks": chunks, "stats": stats})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── Embedding Visualization API ───

@app.route("/api/embeddings/info", methods=["GET"])
def embedding_info():
    """Get embedding model information."""
    try:
        info = get_embedding_info()
        return jsonify(info)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/embeddings/visualize", methods=["POST"])
def visualize_embeddings():
    """Generate 2D coordinates for embedding visualization."""
    data = request.get_json(silent=True)
    if not data or "texts" not in data:
        return jsonify({"error": "Texts array is required."}), 400

    texts = [t.strip() for t in data["texts"] if isinstance(t, str) and t.strip()]
    if len(texts) < 2:
        return jsonify({"error": "At least 2 texts required for visualization."}), 400
    if len(texts) > 100:
        return jsonify({"error": "At most 100 texts can be visualized at once."}), 400

    try:
        embeddings = generate_embeddings(texts)
        coords = reduce_dimensions(embeddings, method="pca", n_components=2)
        sim_matrix = compute_similarity_matrix(texts, embeddings=embeddings)

        points = []
        for i, text in enumerate(texts):
            points.append({
                "text": text[:100],
                "x": round(coords[i][0], 4),
                "y": round(coords[i][1], 4),
                "embedding_preview": [round(v, 4) for v in embeddings[i][:5]]  # First 5 dims
            })

        return jsonify({
            "points": points,
            "similarity_matrix": [[round(v, 4) for v in row] for row in sim_matrix]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── Error Handlers ───

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found."}), 404


@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"error": "Method not allowed."}), 405


@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error."}), 500


# ─── Main ───

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    logger.info(f"Starting Vector DB Explorer on port {port}")
    app.run(host="0.0.0.0", port=port, debug=debug)
