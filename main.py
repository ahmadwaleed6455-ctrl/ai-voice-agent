import os
from dotenv import load_dotenv

# Ye function aapki .env file se keys ko chupke se utha lega
load_dotenv()

# Variables mein keys ko assign karna
deepgram_key = os.getenv("DEEPGRAM_API_KEY")
groq_key = os.getenv("GROQ_API_KEY")
google_key = os.getenv("GOOGLE_API_KEY")

# Check karna ki keys aayin ya nahi (Hum keys print nahi karenge security ke liye)
if deepgram_key and groq_key and google_key:
    print("Mubarak ho! Saari API Keys successfully load ho gayi hain. 🎉")
else:
    print("Oops! Kuch keys missing hain. Apni .env file dobara check karein.")