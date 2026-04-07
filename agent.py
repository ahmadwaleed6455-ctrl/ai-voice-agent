import asyncio
import os
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv
from livekit import agents
from livekit.agents import JobContext, WorkerOptions, cli
from livekit.agents.voice import AgentSession, Agent
from livekit.plugins import google, simli

load_dotenv(override=True)

# Master Prompt for Personality and Language
BASE_PROMPT = """
You are 'LRH Rahbar', a friendly and professional AI Assistant at Lady Reading Hospital (LRH), Peshawar.
Your mission is to guide patients and attendants through hospital procedures, OPD timings, and locations.

RULES:
1. Speak primarily in Roman Urdu.
2. IMPORTANT: If the user speaks in Pashto (Pukhto), you MUST respond in fluent Pashto. 
3. Use the 'Relevant Hospital Info' provided below to answer accurately. 
4. If the info isn't in the context, politely say you don't have that specific detail but can help with general navigation.
5. Mention specific counter numbers (e.g., Counter 1, Counter 5) and room numbers clearly.
6. Keep responses concise and compassionate.
"""

# --- 1. Helper Function for RAG (Inside Entrypoint to avoid Timeouts) ---
def get_hospital_context(collection, query):
    """Database se relevant hospital workflow nikalne ke liye"""
    try:
        results = collection.query(
            query_texts=[query],
            n_results=2 
        )
        
        context = ""
        # Fix: ChromaDB results['documents'] is [[doc1, doc2]]
        if results['documents'] and len(results['documents']) > 0:
            for doc in results['documents']: 
                context += str(doc) + "\n"
        
        return context if context.strip() else "No specific hospital data found for this query."
    except Exception as e:
        print(f"Error fetching from ChromaDB: {e}")
        return "System error accessing hospital records."

# --- 2. Assistant Class ---
class Assistant(Agent):
    def __init__(self, context_data: str) -> None:
        dynamic_instructions = f"{BASE_PROMPT}\n\nRelevant Hospital Info for this session:\n{context_data}"
        super().__init__(instructions=dynamic_instructions)

# --- 3. Entrypoint (LiveKit Agent Logic) ---
async def entrypoint(ctx: JobContext):
    await ctx.connect()
    print("⏳ Initializing Knowledge Base and Models...")

    # Moving Heavy Imports/Setup inside entrypoint to prevent Startup Timeout
    db_client = chromadb.PersistentClient(path="./chroma_db")
    model_name = "all-MiniLM-L6-v2"
    embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=model_name)
    collection = db_client.get_collection(name="lrh_knowledge", embedding_function=embedding_func)

    print("🚀 LRH Rahbar IS ONLINE (RAG + Gemini 3.1 + Simli Avatar)")

    # Fetching initial context
    initial_context = get_hospital_context(collection, "General OPD timings and Laboratory process")

    session = AgentSession(
        llm=google.realtime.RealtimeModel(
            model="gemini-3.1-flash-live-preview",
            voice="NOVA", 
        )
    )

    # Simli Integration
    simli_key = os.getenv("SIMLI_API_KEY")
    avatar = simli.AvatarSession(
        simli_config=simli.SimliConfig(
            api_key=simli_key,
            face_id="f0ba4efe-7946-45de-9955-c04a04c367b9" 
        )
    )
    
    await avatar.start(session, room=ctx.room)

    await session.start(
        agent=Assistant(initial_context),
        room=ctx.room,
    )

if __name__ == "__main__":
    cli.run_app(WorkerOptions(
        entrypoint_fnc=entrypoint,
        prewarm_fnc=None, # Prevents heavy tasks from blocking the main process
    ))