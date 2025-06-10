from langchain.document_loaders.pdf import PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.vectorstores.chroma import Chroma
from langchain.schema.document import Document
from langchain_community.embeddings.bedrock import BedrockEmbeddings


CHROMA_PATH = "chroma"
DATA_PATH = "data"


def get_emb():
    emb = BedrockEmbeddings(
        credentials_profile_name="default", region_name="us-east-1"
    )

    return emb

def load_docs():
    doc_load = PyPDFDirectoryLoader(DATA_PATH)
    return doc_load.load()

def split_docs_chunks(docs: list[Document]):
    text_split = RecursiveCharacterTextSplitter(
        chunk_size = 800,
        chunk_overlap = 80,
        is_separator_regex = False,
    )

    return text_split.split_documents(docs)

def add_to_chroma(chunks: list[Document]):
    db = Chroma(
        persist_directory = CHROMA_PATH, embedding_function = get_emb()
    )

    chunks_with_id = calculate_chunk_id(chunks)

    existing_items = db.get(include=[])
    existing_ids = set(existing_items["ids"])
    print(f"Number of existing documents in DB: {len(existing_ids)}")

    new_chunks = []
    for chunk in chunks_with_id:
        if chunk.metadata["id"] not in existing_ids:
            new_chunks.append(chunk)

    if len(new_chunks):
        print(f"👉 Adding new documents: {len(new_chunks)}")
        new_chunk_ids = [chunk.metadata["id"] for chunk in new_chunks]
        db.add_documents(new_chunks, ids=new_chunk_ids)
        db.persist()
    else:
        print("✅ No new documents to add")

def calculate_chunk_id(chunks):
    last_page_id = None
    current_chunk_idx = 0

    for ch in chunks:
        source = ch.metadata.get("source")
        page = ch.metadata.get("page")
        current_page_id = f"{source}:{page}"

        if current_page_id == last_page_id:
            current_chunk_idx += 1
        else:
            current_chunk_idx = 0

        chunk_id = f"{current_page_id}:{current_chunk_idx}"
        last_page_id = current_page_id

        ch.metadata["id"] = chunk_id

    return chunks

# def clear_database():
#     if os.path.exists(CHROMA_PATH):
#         shutil.rmtree(CHROMA_PATH)