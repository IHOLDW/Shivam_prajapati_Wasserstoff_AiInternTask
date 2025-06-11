
# 🧠 RAG Chatbot - Document-Aware LLM Chat Application

A powerful Retrieval-Augmented Generation (RAG) chatbot with real-time document processing, source tracking, and semantic understanding. Built using **Flask**, **LangChain**, **Chroma**, and **Ollama** with local models.

---

## 🚀 Features

- 🗂️ Upload multi-format documents: `.pdf`, `.jpeg`, `.png`, `.webp`, `.txt`
- 🧠 Query a locally running LLM or Groq api with document-aware responses
- 🖼️ Built-in OCR for image-based documents using **Tesseract**
- 🔄 Add/remove documents from memory dynamically
- 🧾 View which file (and page number if applicable) contributed to each response
- 📊 Live document processing status with a progress bar
- ✅ Clean and modern web UI

---

## 🛠️ Setup Instructions

### 1. Prerequisites

- Python 3.9+
- Linux/macOS (Tested on Linux)
- **Tesseract OCR**:
    ```bash
    sudo apt update && sudo apt install tesseract-ocr
    ```

- **Ollama** (Install from [https://ollama.com](https://ollama.com)):
    ```bash
    curl -fsSL https://ollama.com/install.sh | sh
    ```

- Pull the required models:
    ```bash
    ollama pull gemma3:9b
    ollama pull nomic-embed-text
    ```

---

## 📦 Installation

1. **Clone the repo**:
    ```bash
    git clone https://github.com/IHOLDW/Shivam_prajapati_Wasserstoff_AiInternTask.git
    cd Shivam_prajapati_Wasserstoff_AiInternTask
    ```

2. **Install Python dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3. **Create `.env` file**:
    ```ini
    GROQ_API_KEY = api_key
    OLLAMA_BASE_URL = base_url
    OLLAMA_MODEL_NAME = gemma3:4b
    OLLAMA_EMBEDDING = nomic-embed-text
    GROQ_MODEL_NAME = gemma2-9b-it
    ALLOWED_EXTENSIONS = .pdf,.txt,.jpeg,.jpg,.png,.webp
    UPLOAD_FOLDER = uploads
    ```

---

## ▶️ Running the Application

Start the Flask server:
```bash
python app.py
```

Visit: [http://localhost:5000](http://localhost:5000)

---

## 💬 Chat Interface Walkthrough

1. **Ask Questions**:
   - Query anything from uploaded documents.
2. **Get Response**:
   - LLM answers with file and page references.
3. **Sources Panel**:
   - Lists clickable links to documents and relevant pages.
4. **Update Memory**:
   - Uncheck files to remove them from vectorstore.
5. **Clear Memory**:
   - One-click full memory wipe (files + vectors).

---

## 📂 Project Structure

```
├── app.py                  # Flask backend with API routes
├── rag_pipeline.py         # LangChain + Unstructured + Chroma logic
├── templates/
│   └── index.html          # Frontend HTML
├── static/
│   ├── style.css           # CSS styling
│   └── script.js           # Client-side logic
├── .env                    # Environment configuration
└── README.md
```

---

## 🧠 Models Used

| Type         | Model Name         | Source          |
|--------------|--------------------|-----------------|
| LLM          | `gemma3:9b`        | via Ollama      |
| Embeddings   | `nomic-embed-text` | via Ollama      |
| OCR          | Tesseract OCR      | System install  |

---

## ⚠️ Notes

- Only files uploaded and processed will be available for question answering.
- You **must** run Ollama in the background before starting the app.

---

