import asyncio
import os
from dotenv import load_dotenv
from livekit import agents
from livekit.agents import JobContext, WorkerOptions, cli
from livekit.agents.voice import AgentSession, Agent
from livekit.plugins import google, simli

load_dotenv(override=True)

# --- 1. CONTEXT INGESTION (File Read Karna) ---
try:
    with open("hospital_data.txt", "r", encoding="utf-8") as f:
        HOSPITAL_DATA = f.read()
except FileNotFoundError:
    print("⚠️ Warning: hospital_data.txt nahi mili!")
    HOSPITAL_DATA = "Data not available."

# --- 2. THE MASTER PROMPT (Direct Feed) ---
BASE_PROMPT = f"""
You are 'LRH Rahbar', a friendly and professional AI Assistant at Lady Reading Hospital (LRH), Peshawar.
Your mission is to guide patients and attendants through hospital procedures, OPD timings, and locations.

ABSOLUTE STRICT RULES:
1. Speak primarily in Roman Urdu.
2. IMPORTANT: If the user speaks in Pashto (Pukhto), you MUST respond in fluent Pashto. 
3. Use the 'COMPLETE HOSPITAL MANUAL' provided below to answer accurately. 
4. NEVER guess or hallucinate schedules. If the info isn't in the manual, politely say you don't have that specific detail.
5. Mention specific counter numbers (e.g., Counter 1, Counter 5) and room numbers clearly.
6. Keep responses extremely concise. Max 2 short sentences. No introductory filler phrases.

COMPLETE HOSPITAL MANUAL:
{HOSPITAL_DATA}
"""

# --- 3. Assistant Class ---
class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions=BASE_PROMPT)

# --- 4. Entrypoint (LiveKit Agent Logic) ---
async def entrypoint(ctx: JobContext):
    await ctx.connect()
    print("⏳ Starting LRH Rahbar Session...")

    session = AgentSession(
        llm=google.realtime.RealtimeModel(
            model="gemini-3.1-flash-live-preview",
            voice="Aoede", 
        )
    )

    # Simli Avatar Integration
    simli_key = os.getenv("SIMLI_API_KEY")
    avatar = simli.AvatarSession(
        simli_config=simli.SimliConfig(
            api_key=simli_key,
            face_id="f0ba4efe-7946-45de-9955-c04a04c367b9" 
        )
    )
    
    await avatar.start(session, room=ctx.room)
    print("🚀 LRH Rahbar IS ONLINE (Context Ingested + Avatar Live)")

    await session.start(
        agent=Assistant(),
        room=ctx.room,
    )

if __name__ == "__main__":
    cli.run_app(WorkerOptions(
        entrypoint_fnc=entrypoint,
        prewarm_fnc=None, 
    ))