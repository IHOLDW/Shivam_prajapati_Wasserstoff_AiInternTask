from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import shutil
from threading import Thread
from werkzeug.utils import secure_filename
from rag_pipeline import process_documents, query_documents, clear_db, modify_learning

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {".pdf", ".webp", ".jpeg", ".png", ".txt", ".jpg"}
MAX_FILE_SIZE_MB = 25

processing_status = {
    "total": 0,
    "current": 0,
    "processing": False,
    "error": None
}

if os.path.exists(UPLOAD_FOLDER):
    shutil.rmtree(UPLOAD_FOLDER)
os.makedirs(UPLOAD_FOLDER)
  
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE_MB * 1024 * 1024

documents_uploaded = []
processed_files = set()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/data', methods=['GET'])
def get_uploaded_files():
    return jsonify({'files': documents_uploaded})

@app.route('/api/clear', methods=['POST'])
def clear_files():
    global processed_files
    processed_files.clear()
    for f in os.listdir(UPLOAD_FOLDER):
        os.remove(os.path.join(UPLOAD_FOLDER, f))
    clear_db()
    documents_uploaded.clear()
    return jsonify({'message': 'Folder cleared.'})

def allowed_file(filename):
    return os.path.splitext(filename)[1] in ALLOWED_EXTENSIONS

@app.route("/api/upload", methods=["POST"])
def upload_files():
    uploaded = request.files.getlist("files[]")
    saved_paths = []

    for file in uploaded:
        filename = secure_filename(file.filename)

        if not allowed_file(filename):
            return jsonify({"error": f"Unsupported file type: {filename}"}), 400

        save_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(save_path)

        if filename not in documents_uploaded:
            documents_uploaded.append(filename)

        if filename not in processed_files:
            saved_paths.append(save_path)
            processed_files.add(filename)

    if saved_paths:
        processing_status["processing"] = True
        processing_status["current"] = 0
        processing_status["total"] = len(saved_paths)
        processing_status["error"] = None

        def process_thread():
            try:
                process_documents(saved_paths, status=processing_status)
            except Exception as e:
                processing_status["error"] = str(e)
                processing_status["processing"] = False
        
        Thread(target=process_thread).start()

    return jsonify({"status": "processing started"})


@app.route("/api/modify_learning", methods=["POST"])
def api_modify_learning():
    global processed_files
    data = request.get_json()
    files_to_delete = data.get("files", [])
    modify_learning(files_to_delete)

    for fname in files_to_delete:
        processed_files.discard(fname)
    
    return jsonify({"message": "Files removed from vector store."})

@app.route("/api/status")
def api_status():
    return jsonify(processing_status)

@app.route('/uploads/<path:filename>')
def serve_uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route('/api/query', methods=['POST'])
def query():
    user_query = request.form.get('query')
    answer = query_documents(user_query)
    page_number = []
    file_name = []
    for i in answer["context"]["texts"]:
        page_number.append(i.metadata.page_number)
        file_name.append(i.metadata.filename)
    return jsonify({'answer': answer["response"], 'page_number': page_number, "file_name": file_name})

if __name__ == '__main__':
    app.run(debug=True)
