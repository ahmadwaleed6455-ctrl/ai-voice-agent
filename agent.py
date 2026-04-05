import asyncio
import os
from dotenv import load_dotenv

# LiveKit 1.5.1 ke Naye Imports (Pipeline khatam, ab sirf Voice)
from livekit import agents
from livekit.agents import JobContext, WorkerOptions, cli
from livekit.agents.voice import AgentSession, Agent
from livekit.plugins import openai, deepgram, silero

# .env load karna
load_dotenv(override=True)

# Knowledge Base Read karna
def load_knowledge_base():
    try:
        with open("data.txt", "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        return "Error: Data file missing!"

async def entrypoint(ctx: JobContext):
    await ctx.connect()
    print("🚀 MIA IS ONLINE (LiveKit 1.5.1 Stable Mode - Restaurant Assistant)")

    my_data = load_knowledge_base()

    # NAYA TAREEQA: Agent class mein instructions define karein
    mia_agent = Agent(
        instructions=(
            "You are Mia, a professional Multi-Restaurant Order Assistant. "
            "You have access to 4 specific restaurants: Fahad Pizza Hub, Karachi Biryani House, Lahore BBQ Nights, and Islamabad Cafe. "
            "\nSTRICT OPERATING RULES:\n"
            "1. Only answer based on the provided Knowledge Base. If information is missing, say: 'I am sorry, that is not available in our current records.'\n"
            "2. If a user asks for an item, check if THAT specific restaurant offers it.\n"
            "3. If a user asks for 'spicy food' or 'beef', recommend the specific restaurant that has it.\n"
            "4. For delivery charges and time, always quote the specific numbers mentioned for that restaurant.\n"
            "5. Do NOT hallucinate or make up any prices.\n"
            "6. Keep responses short, professional, and helpful.\n\n"
            f"--- RESTAURANT DATASET ---\n{my_data}\n--- END DATASET ---"
        )
    )

    # NAYA TAREEQA: VoicePipelineAgent ki jagah ab 'AgentSession' aagaya hai
    session = AgentSession(
        vad=silero.VAD.load(),
        stt=deepgram.STT(),
        llm=openai.LLM(
            model="llama-3.1-8b-instant",
            base_url="https://api.groq.com/openai/v1",
            api_key=os.getenv("GROQ_API_KEY")
        ),
        tts=deepgram.TTS(),
    )

    # Session start karein aur hamara mia_agent isko dedein
    await session.start(room=ctx.room, agent=mia_agent)
    
    # Welcome message (Pehle 'agent.say' tha, ab 'session.say' hota hai)
    await session.say("Hi, I am Mia. Welcome to our Multi-Restaurant service. How can I help you today?", allow_interruptions=True)

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))