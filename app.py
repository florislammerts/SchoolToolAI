# streamlit_ai_study_tool_subscriptions.py

import streamlit as st
import sqlite3
from PyPDF2 import PdfReader
import openai
st.session_state.logged_in = True
from google.cloud import texttospeech
from io import BytesIO
from datetime import datetime

# -----------------------------
# SETUP
# -----------------------------
st.set_page_config(page_title="AI Study Tool (Subscription Ready)", layout="wide")
st.title("🌍 AI Study Tool - Accounts & Subscriptions Prototype")

# OpenAI API
openai.api_key = st.secrets["OPENAI_API_KEY"]

# Google TTS client
client = texttospeech.TextToSpeechClient()

# -----------------------------
# DATABASE
# -----------------------------
conn = sqlite3.connect("users.db")
c = conn.cursor()

# Create tables
c.execute('''CREATE TABLE IF NOT EXISTS users
             (id INTEGER PRIMARY KEY, email TEXT UNIQUE, password TEXT, premium INTEGER)''')
c.execute('''CREATE TABLE IF NOT EXISTS history
             (id INTEGER PRIMARY KEY, user_id INTEGER, book_name TEXT, summary TEXT, timestamp TEXT)''')
conn.commit()

# -----------------------------
# USER AUTHENTICATION
# -----------------------------
def signup(email, password):
    try:
        c.execute("INSERT INTO users (email, password, premium) VALUES (?, ?, ?)", (email, password, 0))
        conn.commit()
        st.success("Account created successfully!")
    except:
        st.error("Email already exists.")

def login(email, password):
    c.execute("SELECT id, premium FROM users WHERE email=? AND password=?", (email, password))
    user = c.fetchone()
    if user:
        st.session_state['user_id'] = user[0]
        st.session_state['premium'] = bool(user[1])
        st.success("Logged in successfully!")
        return True
    else:
        st.error("Invalid credentials")
        return False

# Session
if 'user_id' not in st.session_state:
    st.subheader("🔑 Login / Sign Up")
    option = st.selectbox("Select Option", ["Login", "Sign Up"])
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if option == "Sign Up" and st.button("Sign Up"):
        signup(email, password)
    if option == "Login" and st.button("Login"):
        login(email, password)
else:
    st.subheader(f"Welcome User {st.session_state['user_id']}")

    # -----------------------------
    # BOOK SECTION INPUT
    # -----------------------------
    uploaded_file = st.file_uploader("Upload PDF of the book", type=["pdf"])
    book_name = st.text_input("Book Name")
    chapters = st.text_input("Chapters (e.g., 1-3)")
    pages = st.text_input("Pages (optional)")
    
    # Usage Limit for Free Users
    if not st.session_state['premium']:
        st.info("Free account: Maximum 2 summaries per day")
        # Count today's summaries
        today = datetime.today().date()
        c.execute("SELECT COUNT(*) FROM history WHERE user_id=? AND date(timestamp)=?", (st.session_state['user_id'], str(today)))
        count_today = c.fetchone()[0]
        if count_today >= 2:
            st.warning("You have reached your daily free summary limit. Upgrade to premium for unlimited use.")
    
    if st.button("Generate Summary") and uploaded_file:
        # Extract text
        reader = PdfReader(uploaded_file)
        text = "\n\n".join([p.extract_text() for p in reader.pages])
        
        # Generate summary
        prompt = f"Summarize the book '{book_name}', chapters '{chapters}'. Text:\n{text}"
        response = openai.Completion.create(engine="text-davinci-003", prompt=prompt, max_tokens=1000)
        summary = response.choices[0].text.strip()
        
        st.subheader("📖 Summary")
        st.write(summary)
        
        # Save history
        c.execute("INSERT INTO history (user_id, book_name, summary, timestamp) VALUES (?, ?, ?, ?)",
                  (st.session_state['user_id'], book_name, summary, str(datetime.now())))
        conn.commit()
        
        # TTS (English example)
        synthesis_input = texttospeech.SynthesisInput(text=summary)
        voice = texttospeech.VoiceSelectionParams(language_code="en-US", name="en-US-Wavenet-D")
        audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
        audio_response = client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
        audio_bytes = BytesIO(audio_response.audio_content)
        st.audio(audio_bytes, format="audio/mp3")
        
        st.download_button("Download Summary TXT", summary, file_name=f"{book_name}_summary.txt")
        st.download_button("Download Audio MP3", audio_bytes, file_name=f"{book_name}_summary.mp3", mime="audio/mp3")
