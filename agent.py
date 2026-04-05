import asyncio

import os

from dotenv import load_dotenv



from livekit import agents

from livekit.agents import JobContext, WorkerOptions, cli

from livekit.agents.voice import AgentSession, Agent

from livekit.plugins import google



# .env file load karna (Make sure GOOGLE_API_KEY is in your .env)

load_dotenv(override=True)



# Knowledge Base Read karna

def load_knowledge_base():

    try:

        with open("data.txt", "r", encoding="utf-8") as file:

            return file.read()

    except FileNotFoundError:

        return "Error: Data file missing!"



my_data = load_knowledge_base()



# 1. SYSTEM PROMPT (Simplified to stop 1007 errors)

SYSTEM_PROMPT = f"""

You are Sara, the official OPD Schedule Assistant for Lady Reading Hospital (LRH).

You help patients and staff with accurate doctor schedules.



STRICT OPERATING RULES:

1. Only answer based on the provided Hospital Data.

2. If a user asks for a specific doctor or department, check the schedule.

3. Keep responses very short and professional.

4. LANGUAGE RULE: Respond in the same language the user speaks (Urdu, English, Pashto).



--- HOSPITAL DATASET ---

{my_data}

--- END DATASET ---

"""



# 2. ASSISTANT CLASS (Agent structure)

class Assistant(Agent):

    def __init__(self) -> None:

        super().__init__(

            instructions=SYSTEM_PROMPT

        )



async def entrypoint(ctx: JobContext):

    await ctx.connect()

    print("🚀 fahad IS ONLINE (Gemini 3.1 Live Public Model)")



    # 3. AGENT SESSION

    session = AgentSession(

        llm=google.realtime.RealtimeModel(

            model="gemini-3.1-flash-live-preview", # <-- WAPAS YAHI LIKH DEIN!

            voice="Puck",

        )

    )



    # 4. START SESSION

    await session.start(

        agent=Assistant(),

        room=ctx.room,

    )

   

    # Note: Humne yahan se 'say()' hata diya hai.

    # Jab Connect ho jaye, aap mic par bolein "Hello Mia", aur wo bolna shuru karegi.



if __name__ == "__main__":

    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))