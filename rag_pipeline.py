import os
import uuid
import pytesseract
from PIL import Image
from dotenv import load_dotenv
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from unstructured.partition.pdf import partition_pdf
from unstructured.partition.text import partition_text
from langchain.schema.document import Document
from langchain.vectorstores import Chroma
from langchain.retrievers.multi_vector import MultiVectorRetriever, SearchType
from langchain.storage import InMemoryStore
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.messages import HumanMessage
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

OLLAMA_MODEL_NAME = os.getenv("OLLAMA_MODEL_NAME")
OLLAMA_EMBEDDING = os.getenv("OLLAMA_EMBEDDING")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL_NAME = os.getenv("GROQ_MODEL_NAME")

processed_file_dict_ids = {}

text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=100   
)
if OLLAMA_BASE_URL:
    chat_model = ChatOllama(
        model = OLLAMA_MODEL_NAME,
        base_url = OLLAMA_BASE_URL
    )
if GROQ_API_KEY:
    chat_groq = ChatGroq(
        model = GROQ_MODEL_NAME,
        api_key = GROQ_API_KEY
    )
if OLLAMA_EMBEDDING and OLLAMA_BASE_URL:
    embedding = OllamaEmbeddings(model = OLLAMA_EMBEDDING, base_url = OLLAMA_BASE_URL)

vector_store = Chroma(collection_name = "storage_vector", embedding_function = embedding)
storage = InMemoryStore()
id_key = 'doc_id'
retriever= MultiVectorRetriever(
    vectorstore = vector_store,
    docstore = storage,
    id_key = id_key,
    search_type = SearchType.mmr,
            search_kwargs = {
            "k": 5,       
            "fetch_k": 15,
            "lambda_mult": 0.5
    }
)


#add a try catch here
#this funtions helps user to delete partical files from database
def modify_learning(files_to_delete: list):
    global processed_file_dict_ids

    for i in files_to_delete:
        if i not in processed_file_dict_ids:
            continue
        try:
            if i.lower().endswith('.pdf'):
                vector_id = processed_file_dict_ids[i]["pdf_docstore_id"]
                vector_store.delete(vector_id)
                storage.mdelete(vector_id)
            elif i.lower().endswith('.txt'):
                vector_id = processed_file_dict_ids[i]["txt_docstore_id"]
                vector_store.delete(vector_id)
                storage.mdelete(vector_id)
            else:
                vector_id = processed_file_dict_ids[i]["img_docstore_id"]
                vector_store.delete(vector_id)
                storage.mdelete(vector_id)

            processed_file_dict_ids.pop(i)
        except Exception as e:
            raise Exception(f"unable to update memory: {e}")
        

#this funtion is used to clear all files stored in database, thus reseting memory
def clear_db():
    global vector_store, storage, retriever, processed_file_dict_ids

    try:
        all_vector_ids = vector_store._collection.get()['ids']
        if all_vector_ids:
            vector_store.delete(all_vector_ids)
        
        vector_store = Chroma(
        collection_name="storage_vector",
        embedding_function=embedding
    )
    except Exception as e:
        raise Exception(f"Error deleting from Chroma: {e}")

    try:
        all_doc_ids = list(storage.yield_keys())
        if all_doc_ids:
            storage.mdelete(keys=all_doc_ids)
        
        processed_file_dict_ids = {}
        storage = InMemoryStore()
        retriever = MultiVectorRetriever(
            vectorstore=vector_store,
            docstore=storage,
            id_key='doc_id',
            search_type = SearchType.mmr,
            search_kwargs = {
            "k": 5,       
            "fetch_k": 15,
            "lambda_mult": 0.5
            }
        )
    except Exception as e:
        raise Exception(f"Error deleting from InMemoryStore: {e}")
    

def process_txt(f, file_name, status):
    global processed_file_dict_ids
    try:
        chunk = partition_text(
            filename = f,
            encoding = "utf-8",
            max_characters=10000,
            combine_text_under_n_chars=2000,
            new_after_n_chars=6000,
            chunking_strategy= "by_title"
        )

        texts = []
        for i in chunk:
            if "CompositeElement" in str(type(i)):
                texts.append(i)
        prompt_text = """You are an assistant tasked with summarizing tables and text.
Give a concise summary of the table or text.
Respond only with the summary, no additionnal comment.
Do not start your message by saying "Here is a summary" or anything like that.
Just give the summary as it is.
text chunk: {element}
"""
        prompt = ChatPromptTemplate.from_template(prompt_text)
        summarize_chain = {"element": lambda x: x} | prompt | chat_groq | StrOutputParser()
        text_summaries = summarize_chain.batch(texts, {"max_concurrency": 3})
        doc_idss = [str(uuid.uuid4()) for _ in texts]
        summary_text = []
        for i, summary in enumerate(text_summaries):
            page_num = texts[i].metadata.page_number
            summary_text.append(Document(
                page_content=summary,
                metadata={
                    id_key: doc_idss[i],
                    "file_name": file_name,
                    "page_number": page_num
                }
            ))
        retriever.vectorstore.add_documents(summary_text, ids = doc_idss)
        retriever.docstore.mset(list(zip(doc_idss, texts)))
        processed_file_dict_ids[str(file_name)] = {
            "txt_docstore_id": doc_idss,
            "txt_vectorstore_id": doc_idss
        }
    except Exception as e:
        if status:
            status["error"] = f"Error extracting text: {str(e)}"
            status["processing"] = False
        return
    
    
def process_img(f, file_name, status):
    global processed_file_dict_ids

    try:
        img = Image.open(f)
        img = img.convert('L')
        text = pytesseract.image_to_string(img)

        if len(text.strip()) > 0:
            with open(f"{file_name}", "w", encoding="utf-8") as txt_file:
                txt_file.write(text)
            chunks = partition_text(
            filename = file_name,
            chunking_strategy="by_title",
            max_characters=10000,
            combine_text_under_n_chars=2000,
            new_after_n_chars=6000
            )

            texts = []
            for i in chunks:
                if "CompositeElement" in str(type(i)):
                    i.metadata.filename = file_name
                    texts.append(i)

            prompt_text = """The text that is given to you is extracted from a image.
If there are some questions asked in the image do not answer them unless told to do so,
just summarize the text, is very short form as you are trying to tell whats in the image.
if questions are present just get a brief of them for future answering purpose,
And at the starting do state that the this is the infomation accoring to the text in the image
text_extracted_from_image = {element}""" 

            prompt = ChatPromptTemplate.from_template(prompt_text)
            summarize_chain = {"element": lambda x: x} | prompt | chat_groq | StrOutputParser()
            text_summaries = summarize_chain.batch(texts, {"max_concurrency": 3})
            doc_idss = [str(uuid.uuid4()) for _ in texts]
            summary_text = []
            for i, summary in enumerate(text_summaries):
                page_num = texts[i].metadata.page_number
                summary_text.append(Document(
                    page_content=summary,
                    metadata={
                        id_key: doc_idss[i],
                        "file_name": file_name,
                        "page_number": page_num
                    }
                ))
            retriever.vectorstore.add_documents(summary_text, ids = doc_idss)
            retriever.docstore.mset(list(zip(doc_idss, texts)))
            processed_file_dict_ids[str(file_name)] = {
                "img_docstore_id": doc_idss,
                "img_vectorstore_id": doc_idss
            }

            if os.path.exists(file_name):
                os.remove(file_name)
    except Exception as e:
        if status:
            status["error"] = f"Error extracting text: {str(e)}"
            status["processing"] = False
        return


def process_pdf(f, file_name, status):
    global processed_file_dict_ids

    try:
        chunk = partition_pdf(
            filename= f,
            infer_table_structure=False,
            strategy="hi_res",
            extract_image_block_to_payload=True,
            chunking_strategy="by_title",
            max_characters=10000,
            combine_text_under_n_chars=2000,
            new_after_n_chars=6000,
        )
        texts = []
        for ch in chunk:
            if "CompositeElement" in str(type((ch))):
                texts.append(ch)
            
        prompt_text = """You are an assistant tasked with summarizing tables and text.
Give a concise summary of the table or text.
Respond only with the summary, no additionnal comment.
Do not start your message by saying "Here is a summary" or anything like that.
Just give the summary as it is.
text chunk: {element}
"""
        prompt = ChatPromptTemplate.from_template(prompt_text)
        summarize_chain = {"element": lambda x: x} | prompt | chat_groq | StrOutputParser()
        text_summaries = summarize_chain.batch(texts, {"max_concurrency": 3})

        doc_idss = [str(uuid.uuid4()) for _ in texts]
        summary_text = []
        for i, summary in enumerate(text_summaries):
            page_num = texts[i].metadata.page_number
            summary_text.append(Document(
                page_content=summary,
                metadata={
                    id_key: doc_idss[i],
                    "file_name": file_name,
                    "page_number": page_num
                }
            ))

        
        retriever.vectorstore.add_documents(summary_text, ids = doc_idss)
        retriever.docstore.mset(list(zip(doc_idss, texts)))
        
        processed_file_dict_ids[str(file_name)] = {
            "pdf_docstore_id": doc_idss,
            "pdf_vectorstore_id": doc_idss
        }
    except Exception as e:
        if status:
            status["error"] = f"Error processing pdf: {str(e)}"
            status["processing"] = False
        return


#main part of the pipeline here all processing of documents happen, first it divides the file into chunks, then creates a summary using llm.
#After that it stores embedding and document chunk into database
def process_documents(file_paths, status=None):

    for i, f in enumerate(file_paths):
        file_name = os.path.basename(f)
        if f.lower().endswith('.txt'):
            process_txt(f, file_name, status)

        if f.lower().endswith('.pdf'):
            process_pdf(f, file_name, status)

        if f.lower().endswith('.jpeg') or f.lower().endswith('.png') or f.lower().endswith('.webp') or f.lower().endswith('.jpg'):
            process_img(f, file_name, status)

        if status:
            status["current"] = i + 1

    if status:
        status["processing"] = False

#old method used to sort documne based on image and text.
#earlier vision llm was used to generate the summary of image rather then using ocr to extract the text
#not needed as of now, will remove in future
def parse_docs(docs):
    text = []
    for doc in docs:
        text.append(doc)

    return {"texts": text}

#prompt building
#add a feature in .env file where user can change the prompt, enabling them to generate different responses
def build_prompt(kwargs):
    docs_by_type = kwargs["context"]
    user_question = kwargs["question"]

    context_text = ""
    context_chunks = []

        
    for element in docs_by_type["texts"]:
        if isinstance(element, str):
            context_chunks.append(element)
        elif hasattr(element, "text"): 
            context_chunks.append(element.text)
        else:
            context_chunks.append(str(element))
       
    context_text = "\n\n".join(context_chunks)

    prompt_template = f"""Answer the question based only on the following context, which can include text.
if context is not given strictly do not answer it, just say context not given.
Context: {context_text}
Question: {user_question}
Answer the question only if context is given.
"""

    prompt_content = [{"type": "text", "text": prompt_template}]

    return ChatPromptTemplate.from_messages(
        [
            HumanMessage(content=prompt_content),
        ]
    )

#basic funtions to generate the response from the context and user query
def query_documents(prompt):
    try:
        chain = {
            "context": retriever | RunnableLambda(parse_docs),
            "question": RunnablePassthrough(),
        } | RunnablePassthrough().assign(
            response=(
                RunnableLambda(build_prompt)
                | chat_groq
                | StrOutputParser()
            )
        )
        return chain.invoke(prompt)
    except Exception as e:
        raise Exception(f"Error generating response: {e}")