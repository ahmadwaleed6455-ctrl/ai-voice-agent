import os
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from groq import Groq  # <-- Gemini ki jagah Groq
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Groq Setup
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Hospital Data Read Karein
with open("hospital_data.txt", "r") as f:
    hospital_info = f.read()

@app.route("/whatsapp", methods=['POST'])
def whatsapp_reply():
    incoming_msg = request.values.get('Body', '').lower()
    
    # Prompt tayar karein
    prompt = f"You are Sara, an OPD assistant at LRH Hospital. Use this data: {hospital_info}. Answer briefly in Urdu/Hindi: {incoming_msg}"
    
    # Groq Model Call (Llama 3 use kar rahe hain)
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
    )

    # Response nikalna
    reply_text = completion.choices''.message.content

    # Twilio ko jawab bhejna
    resp = MessagingResponse()
    resp.message(reply_text)

    return str(resp)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
