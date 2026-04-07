import asyncio
import os
from dotenv import load_dotenv
from livekit import agents
from livekit.agents import JobContext, WorkerOptions, cli
from livekit.agents.voice import AgentSession, Agent
from livekit.plugins import google, simli

load_dotenv(override=True)

# Knowledge Base
def load_knowledge_base():
    try:
        with open("data.txt", "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        return "Hospital data missing."

my_data = load_knowledge_base()

SYSTEM_PROMPT = f"You are AI Assistant at LRH. Use this data: {my_data}. Speak Roman Urdu."

class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions=SYSTEM_PROMPT)

async def entrypoint(ctx: JobContext):
    await ctx.connect()
    print("🚀 AI Assistant IS ONLINE (Gemini 3.1 + Simli Avatar)")

    # 1. Realtime Model Session
    session = AgentSession(
        llm=google.realtime.RealtimeModel(
            model="gemini-3.1-flash-live-preview",
            voice="NOVA",
        )
    )

    # 2. Simli Avatar Setup
    simli_key = os.getenv("SIMLI_API_KEY")
    avatar = simli.AvatarSession(
        simli_config=simli.SimliConfig(
            api_key=simli_key,
            face_id="dd10cb5a-d31d-4f12-b69f-6db3383c006e" 
        )
    )
    
    # Pehle avatar ko start karein (Bina kisi extra numbers ke)
    await avatar.start(session, room=ctx.room)

    # 3. Session ko assistant ke sath start karein
    await session.start(
        agent=Assistant(),
        room=ctx.room,
    )

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
