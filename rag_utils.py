import os
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader

# Ye model text ko numbers (vectors) mein badlega - Local aur Free
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
CHROMA_PATH = "chroma_db"

def process_file_to_vdb(file_path):
    # 1. File Load karna
    if file_path.endswith(".pdf"):
        loader = PyPDFLoader(file_path)
    else:
        loader = TextLoader(file_path, encoding="utf-8")
    
    documents = loader.load()

    # 2. Text Splitting (1000 chote tukron mein todna)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = text_splitter.split_documents(documents)

    # 3. Chroma Database banana aur save karna
    vector_db = Chroma.from_documents(
        documents=chunks, 
        embedding=embeddings, 
        persist_directory=CHROMA_PATH
    )
    return "Vector Database Updated Successfully!"

def get_relevant_context(query):
    # Agent is function ko call karega data dhoondne ke liye
    if not os.path.exists(CHROMA_PATH):
        return "Database is empty. No data found."
    
    vector_db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embeddings)
    results = vector_db.similarity_search(query, k=1) # Top 1 matching tukray nikalna
    
    context_text = "\n\n---\n\n".join([doc.page_content for doc in results])
    return context_text