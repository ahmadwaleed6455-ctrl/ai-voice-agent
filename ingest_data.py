import chromadb
from chromadb.utils import embedding_functions

# 1. ChromaDB Client setup
client = chromadb.PersistentClient(path="./chroma_db")

# 2. Embedding function (Jo text ko numbers/vectors mein badle ga)
# Ye free hai aur locally chalta hai
model_name = "all-MiniLM-L6-v2"
embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=model_name)

# 3. Collection banayein (Jaise SQL mein table hota hai)
collection = client.get_or_create_collection(name="lrh_knowledge", embedding_function=embedding_func)

# 4. Data read karein aur chunks mein store karein
def load_hospital_data():
    with open("hospital_data.txt", "r") as f:
        content = f.read()
        # Chunks mein divide karein (Simple example: by lines or paragraphs)
        chunks = content.split('\n\n') 
        
        for idx, chunk in enumerate(chunks):
            if chunk.strip():
                collection.add(
                    documents=[chunk],
                    ids=[f"id_{idx}"]
                )
    print("✅ Hospital data ingested into ChromaDB!")

if __name__ == "__main__":
    load_hospital_data()