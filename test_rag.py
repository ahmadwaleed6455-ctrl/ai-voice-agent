import chromadb
from chromadb.utils import embedding_functions

# 1. Database Connection Setup
db_client = chromadb.PersistentClient(path="./chroma_db")
model_name = "all-MiniLM-L6-v2"
embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=model_name)

# 2. Collection Access
collection = db_client.get_collection(name="lrh_knowledge", embedding_function=embedding_func)

def get_relevant_context(user_query):
    try:
        results = collection.query(
            query_texts=[user_query],
            n_results=2
        )
        
        # ChromaDB results['documents'] is a list of lists: [[doc1, doc2]]
        context = ""
        if results['documents'] and len(results['documents']) > 0:
            # Pehli list (top results) uthayen
            for doc in results['documents']:
                context += str(doc) + "\n"
        return context
    except Exception as e:
        return f"Error: {e}"

# 4. Testing the Search
if __name__ == "__main__":
    query = "Surgical Opd kis ki hai Monday ko?" # Aap koi bhi sawal likh sakte hain
    print(f"\n🔍 Searching for: {query}")
    print("-" * 40)
    
    context = get_relevant_context(query)
    
    if context.strip():
        print(f"✅ Found in Database:\n{context}")
    else:
        print("❌ Kuch nahi mila! Check karein ke ingest_data.py sahi chala tha?")