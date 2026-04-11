import os
import json
import uuid
import requests
from flask import Flask, request, jsonify, render_template
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import firebase_admin
from firebase_admin import credentials, firestore
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv
from livekit import api
from google import genai
from google.genai import types

# --- 1. Environment & App Setup ---
load_dotenv()
app = Flask(__name__, template_folder='templates', static_folder='static')

# --- 2. Security Setup (Rate Limiter) ---
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)

# --- 3. Gemini 3 Flash Setup ---
# Groq ki jagah ab Google ka AI dimagh lag gaya hai
ai_client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

# --- 4. Firebase Setup ---
fb_content = os.getenv("FIREBASE_SERVICE_ACCOUNT")
if fb_content:
    try:
        fb_dict = json.loads(fb_content)
        cred = credentials.Certificate(fb_dict)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("✅ Firebase Connected Successfully!")
    except Exception as e:
        print(f"❌ Firebase Error: {e}")
else:
    print("⚠️ Error: FIREBASE_SERVICE_ACCOUNT not found!")

def get_user_status(user_id):
    """Check user status from Firebase (Premium vs Free)"""
    try:
        user_ref = db.collection('users').document(user_id).get()
        if user_ref.exists:
            return user_ref.to_dict().get('status', 'free')
        return 'free'
    except:
        return 'free'

# --- 5. Hospital Data Read ---
try:
    with open("hospital_data.txt", "r", encoding="utf-8") as f:
        hospital_info = f.read()
except FileNotFoundError:
    hospital_info = "Hospital data not available."

# --- 🚀 ROUTES (Raste) ---

# Home Page (Frontend Render)
@app.route('/')
def index():
    return render_template('index.html')

# Voice Token for Avatar (With Call Limit logic)
@app.route('/get_voice_token')
@limiter.limit("5 per hour") # Free IPs ko din mein limited calls
def get_voice_token():
    user_id = request.args.get('user_id', 'anonymous')
    status = get_user_status(user_id)
    
    room_name = f"lrh-room-{uuid.uuid4().hex[:6]}" 
    participant_identity = f"user_{uuid.uuid4().hex[:4]}"
    
    token = api.AccessToken(
        os.getenv("LIVEKIT_API_KEY"),
        os.getenv("LIVEKIT_API_SECRET")
    ).with_identity(participant_identity) \
     .with_grants(api.VideoGrants(room_join=True, room=room_name))
     
    return jsonify({
        "token": token.to_jwt(),
        "url": os.getenv("LIVEKIT_URL"),
        "status": status,
        "timeout": 60 if status == 'free' else 600 # 1 min for free, 10 min for premium
    })

# Web Chat API
@app.route('/chat', methods=['POST'])
@limiter.limit("20 per hour")
def web_chat():
    data = request.json
    user_msg = data.get('message')
    user_id = data.get('user_id', 'anonymous')

    prompt = f"""
    System: You are 'LRH Rahbar', a helpful AI assistant at Lady Reading Hospital. 
    Answer in Roman Urdu, Urdu, or Pashto based on user's language. 
    Use this data: {hospital_info}
    User: {user_msg}
    LRH Rahbar:"""
    
    # --- NAYI GEMINI 3 FLASH API CALL ---
    response = ai_client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.2,
        )
    )
    
    reply = response.text

    if fb_content:
        db.collection('chats').add({
            'user_id': user_id,
            'message': user_msg,
            'reply': reply,
            'timestamp': firestore.SERVER_TIMESTAMP
        })

    return jsonify({'reply': reply})

@app.route("/sms-gateway", methods=['POST'])
def sms_gateway_reply():
    try:
        # 1. Pehle check karein ke data kis format mein aa raha hai
        # SMSGateway24 aksar Form data bhejta hai, kuch apps JSON bhejti hain
        incoming_data = request.form if request.form else request.json
        
        if not incoming_data:
            print("⚠️ No data received in request!")
            return "No data", 400

        # 2. Data nikalne ki koshish (Alag alag apps ke liye generic check)
        incoming_msg = incoming_data.get('body') or incoming_data.get('message') or incoming_data.get('text')
        sender_number = incoming_data.get('address') or incoming_data.get('phone') or incoming_data.get('from')

        if not incoming_msg or not sender_number:
            print(f"⚠️ Missing info: Msg={incoming_msg}, Phone={sender_number}")
            return "Missing info", 400

        print(f"📱 SMS Received: {incoming_msg} from {sender_number}")

        # 3. Gemini 3.1 Pro Call
        prompt = f"System: You are LRH Rahbar. Reply briefly in Roman Urdu/Pashto. Data: {hospital_info}\nUser: {incoming_msg}"
        
        # Safe API Call
        try:
            response = ai_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            reply_text = response.text
        except Exception as ai_err:
            print(f"❌ Gemini Error: {ai_err}")
            reply_text = "Maaf kijiye, system thora busy hai."

     # --- SMS GATEWAY 24 FINAL SEND (As per Docs) ---
        api_token = os.getenv("SMS_GATEWAY_TOKEN")
        device_id = os.getenv("SMS_DEVICE_ID")

        if api_token and device_id:
            # DOCUMENTATION KA SAHI ENDPOINT:
            api_url = "https://smsgateway24.com/getdata/addsms"
            
            payload = {
                "token": api_token,
                "sendto": sender_number,
                "body": reply_text,
                "device_id": device_id,
                "sim": 1,        # 1 for Onic, 0 for Jazz
                "urgent": 1      # High priority
            }
            
            # Request bhej rahe hain (Form Data format mein)
            r = requests.post(api_url, data=payload)
            
            # Response check
            try:
                res_json = r.json()
                if res_json.get('error') == 0:
                    print(f"🎯 SUCCESS! SMS ID: {res_json.get('sms_id')} - Jawab bhej diya gaya.")
                else:
                    print(f"❌ Gateway Error: {res_json.get('message')}")
            except:
                # Agar JSON na ho toh error filter
                if "404" in r.text:
                    print("❌ Abhi bhi 404 aa raha hai! Link check karein.")
                else:
                    print(f"⚠️ Raw Response: {r.text[:100]}")

        else:
            print("❌ Error: .env mein Token ya Device ID missing hai!")

        return "OK", 200

    except Exception as e:
        print(f"🔥 Major Crash: {e}")
        return "Internal Server Error", 500
    
# WhatsApp Route (Twilio)
@app.route("/whatsapp", methods=['POST'])
def whatsapp_reply():
    incoming_msg = request.values.get('Body', '').lower()
    
    prompt = f"""
    System: You are 'LRH Rahbar', a helpful AI assistant at Lady Reading Hospital. 
    Answer in Roman Urdu, Urdu, or Pashto based on user's language. Keep answers brief for WhatsApp.
    Use this data: {hospital_info}
    User: {incoming_msg}
    LRH Rahbar:"""
    
    # --- NAYI GEMINI 3 FLASH API CALL ---
    response = ai_client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.2,
        )
    )
    
    reply_text = response.text
    resp = MessagingResponse()
    resp.message(reply_text)
    return str(resp)

# --- 🏁 RUN APP ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
