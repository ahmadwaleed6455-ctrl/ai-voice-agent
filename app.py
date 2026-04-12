import os
import json
import uuid
import requests
from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import firebase_admin
from firebase_admin import credentials, firestore
from firebase_admin import auth as firebase_auth
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv
from livekit import api
from google import genai
from google.genai import types

# --- 1. Environment & App Setup ---
load_dotenv()
app = Flask(__name__, template_folder='templates', static_folder='static')

# 🔴 YE LINE ZAROOR ADD KAREIN SESSIONS KE LIYE 
app.secret_key = os.getenv("FLASK_SECRET_KEY", "lrh_super_secret_key_2026")

# --- 2. Security Setup (Rate Limiter) ---
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)

# --- 3. Gemini 3 Flash Setup ---
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

# --- 5. Hospital Data Read ---
try:
    with open("hospital_data.txt", "r", encoding="utf-8") as f:
        hospital_info = f.read()
except FileNotFoundError:
    hospital_info = "Hospital data not available."

# ==========================================
# 🛠️ HELPER FUNCTIONS
# ==========================================

def check_admin_access(email):
    # Dono emails daal di hain taake kisi se bhi login karein toh Admin Panel khule
    admins = ["fahadgul253@gmail.com", "fahadgul251@gmail.com", "ahmad.waleed6455@gmail.com"] 
    return email in admins

def get_user_status(user_id):
    """Check user status from Firebase (Premium vs Free)"""
    try:
        user_ref = db.collection('users').document(user_id).get()
        if user_ref.exists:
            return user_ref.to_dict().get('status', 'free')
        return 'free'
    except:
        return 'free'

# ==========================================
# 🚀 ROUTES (WEB PAGES)
# ==========================================

# --- MAIN ROUTE (Chat Interface) ---
@app.route('/')
def index():
    # Session se user ki details nikal rahe hain, agar nahi toh 'Guest' banega
    role = session.get('role', 'guest')
    name = session.get('name', 'Guest User')
    
    # Message counter initialize kar rahe hain
    if 'msg_count' not in session:
        session['msg_count'] = 0

    # Ab har koi index.html dekh sakta hai, lekin limits alag hongi
    return render_template('index.html', role=role, name=name)

# --- LOGIN PAGE ROUTE ---
@app.route('/auth')
def auth_page():
    # .env se keys nikal kar dictionary bana rahe hain
    fb_config = {
        "apiKey": os.getenv("FIREBASE_API_KEY"),
        "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN"),
        "projectId": os.getenv("FIREBASE_PROJECT_ID"),
        "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET"),
        "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID"),
        "appId": os.getenv("FIREBASE_APP_ID"),
        "measurementId": os.getenv("FIREBASE_MEASUREMENT_ID")
    }
    # Ye data auth.html ko bhej rahe hain
    return render_template('auth.html', fb_config=fb_config)

# --- LOGIN VERIFICATION ---
@app.route('/login_success', methods=['POST'])
def login_success():
    data = request.json
    user_email = data.get('email')
    
    if not user_email:
        return jsonify({"error": "No email provided"}), 400

    session['user'] = user_email
    # Extract name from email for display (e.g., fahadgul253)
    session['name'] = user_email.split('@')
    session['msg_count'] = 0 # Login par counter reset
    
    if check_admin_access(user_email):
        session['role'] = 'admin'
        return jsonify({"redirect": "/"}) # Admin ko bhi pehle chat par bhejenge, wo upar button se dashboard jayega
    
    session['role'] = 'user'
    return jsonify({"redirect": "/"})

# --- 🛡️ MASTER ADMIN DASHBOARD ---
@app.route('/admin')
def admin_dashboard():
    if session.get('role') != 'admin':
        return "Access Denied: 🛑 Sirf Master Admin yahan aa sakte hain.", 403
    return render_template('admin.html')

# --- LOGOUT ROUTE ---
@app.route('/logout')
def logout():
    session.clear() 
    return redirect(url_for('index'))

# ==========================================
# 🤖 ROUTES (AI & APIS)
# ==========================================

# Voice Token for Avatar (Time Limits)
@app.route('/get_voice_token')
@limiter.limit("5 per hour") 
def get_voice_token():
    role = session.get('role', 'guest')
    
    # ⏱️ TIME LIMITS LOGIC
    if role == 'guest':
        call_timeout = 60    # 1 Minute
    elif role == 'user':
        call_timeout = 120   # 2 Minutes
    else:
        call_timeout = 3600  # Admin: 60 Minutes (Unlimited)
        
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
        "timeout": call_timeout
    })

# Web Chat API (Message Limits)
@app.route('/chat', methods=['POST'])
@limiter.limit("50 per hour")
def web_chat():
    data = request.json
    user_msg = data.get('message')
    
    role = session.get('role', 'guest')
    count = session.get('msg_count', 0)

    # 🛑 MESSAGE LIMITS LOGIC
    if role == 'guest' and count >= 10:
        return jsonify({'reply': "🛑 Guest Limit Reached! Aapne 10 messages poore kar liye hain. Mazeed baat karne ke liye baraye karam Login karein."})
    elif role == 'user' and count >= 10:
        return jsonify({'reply': "🛑 User Limit Reached! Aapke ID ke 10 messages poore ho gaye hain."})

    # Agar Admin nahi hai toh counter barao
    if role != 'admin':
        session['msg_count'] = count + 1
        session.modified = True

    prompt = f"""
    System: You are 'LRH Rahbar', a helpful AI assistant at Lady Reading Hospital. 
    Answer in Roman Urdu, Urdu, or Pashto based on user's language. 
    Use this data: {hospital_info}
    User: {user_msg}
    LRH Rahbar:"""
    
    response = ai_client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.2)
    )
    
    reply = response.text

    if fb_content:
        db.collection('chats').add({
            'user_id': session.get('user', 'anonymous'),
            'role': role,
            'message': user_msg,
            'reply': reply,
            'timestamp': firestore.SERVER_TIMESTAMP
        })

    return jsonify({'reply': reply})

# SMS Gateway API
@app.route("/sms-gateway", methods=['POST'])
def sms_gateway_reply():
    try:
        incoming_data = request.form if request.form else request.json
        
        if not incoming_data:
            return "No data", 400

        incoming_msg = incoming_data.get('body') or incoming_data.get('message') or incoming_data.get('text')
        sender_number = incoming_data.get('address') or incoming_data.get('phone') or incoming_data.get('from')

        if not incoming_msg or not sender_number:
            return "Missing info", 400

        print(f"📱 SMS Received: {incoming_msg} from {sender_number}")

        prompt = f"System: You are LRH Rahbar. Reply briefly in Roman Urdu/Pashto. Data: {hospital_info}\nUser: {incoming_msg}"
        
        try:
            response = ai_client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
            reply_text = response.text
        except Exception as ai_err:
            print(f"❌ Gemini Error: {ai_err}")
            reply_text = "Maaf kijiye, system thora busy hai."

        api_token = os.getenv("SMS_GATEWAY_TOKEN")
        device_id = os.getenv("SMS_DEVICE_ID")

        if api_token and device_id:
            api_url = "https://smsgateway24.com/getdata/addsms"
            payload = {
                "token": api_token,
                "sendto": sender_number,
                "body": reply_text,
                "device_id": device_id,
                "sim": 1,        
                "urgent": 1      
            }
            
            r = requests.post(api_url, data=payload)
            
            try:
                res_json = r.json()
                if res_json.get('error') == 0:
                    print(f"🎯 SUCCESS! SMS ID: {res_json.get('sms_id')} - Jawab bhej diya gaya.")
                else:
                    print(f"❌ Gateway Error: {res_json.get('message')}")
            except:
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
    
    response = ai_client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.2)
    )
    
    reply_text = response.text
    resp = MessagingResponse()
    resp.message(reply_text)
    return str(resp)

# ==========================================
# 🏁 RUN APP (MANDATORY AT THE BOTTOM)
# ==========================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
