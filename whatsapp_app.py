import os
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Groq Setup
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Hospital Data Read Karein
with open("hospital_data.txt", "r", encoding="utf-8") as f:
    hospital_info = f.read()

@app.route("/whatsapp", methods=['POST'])
def whatsapp_reply():
    incoming_msg = request.values.get('Body', '').lower()
    
    # Prompt tayar karein
    prompt = f"""
    You are Sara, an OPD assistant at LRH Hospital.
    Use this data: {hospital_info}
    Answer briefly in Urdu/Hindi.
    User: {incoming_msg}
    """

    # Groq Model Call
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are a helpful hospital assistant."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )

    # Correct response extraction
    reply_text = completion.choices[0].message.content

    # Twilio response
    resp = MessagingResponse()
    resp.message(reply_text)

    return str(resp)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
