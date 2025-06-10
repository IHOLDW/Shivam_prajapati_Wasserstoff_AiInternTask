from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
from rag_pipeline import process_documents, query_documents

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

processing_status = {"processing": False}

@app.route("/api/upload", methods=["POST"])
def upload():
    files = request.files.getlist("files[]")
    saved_files = []
    for f in files:
        filepath = os.path.join(UPLOAD_FOLDER, f.filename)
        f.save(filepath)
        saved_files.append(f.filename)
    
    processing_status["processing"] = True
    process_documents(UPLOAD_FOLDER)
    processing_status["processing"] = False
    return jsonify({"files": saved_files})

@app.route("/api/status", methods=["GET"])
def status():
    return jsonify({"processing": processing_status["processing"]})

@app.route("/api/query", methods=["POST"])
def query():
    query_text = request.form.get("query")
    try:
        response = query_documents(query_text)
        return jsonify({"answer": response})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    if path != "" and os.path.exists("templates/" + path):
        return send_from_directory("templates", path)
    else:
        return send_from_directory("templates", "index.html")

if __name__ == "__main__":
    app.run(debug=True)
