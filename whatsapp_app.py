import os
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from google import genai
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Gemini Setup
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

# Hospital Data Read Karein
with open("hospital_data.txt", "r") as f:
    hospital_info = f.read()

@app.route("/whatsapp", methods=['POST'])
def whatsapp_reply():
    # User ka message lena
    incoming_msg = request.values.get('Body', '').lower()
    
    # Gemini se jawab mangna (Context ke sath)
    prompt = f"You are Sara, an OPD assistant at LRH Hospital. Use this data: {hospital_info}. Answer this patient's question briefly in Urdu/Hindi: {incoming_msg}"
    
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt
    )

    # Twilio ko jawab bhejna
    resp = MessagingResponse()
    msg = resp.message()
    msg.body(response.text)

    return str(resp)

if __name__ == "__main__":
    # Render hamesha 'PORT' naam ka variable deta hai
    port = int(os.environ.get("PORT", 8080)) 
    # Ab ye Render par uski marzi ka port lega, aur laptop par 8080
    app.run(host='0.0.0.0', port=port)