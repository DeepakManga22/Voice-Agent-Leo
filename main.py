import os
import logging
import tempfile
import shutil
from datetime import datetime
import urllib.parse
import asyncio
import httpx
from fastapi import FastAPI, UploadFile, File, HTTPException, Path as ApiPath
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path as FSPath
from dotenv import load_dotenv

import assemblyai as aai

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = FastAPI()

# Load API keys from environment variables
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
MURF_API_KEY = os.getenv("MURF_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")

for key, value in [
    ("ASSEMBLYAI_API_KEY", ASSEMBLYAI_API_KEY),
    ("MURF_API_KEY", MURF_API_KEY),
    ("GEMINI_API_KEY", GEMINI_API_KEY),
    ("NEWSAPI_KEY", NEWSAPI_KEY),
]:
    if not value:
        raise RuntimeError(f"{key} not set in environment")

# AssemblyAI initialization
aai.settings.api_key = ASSEMBLYAI_API_KEY
transcriber = aai.Transcriber()

# Create directories
UPLOADS_DIR = FSPath("uploads")
UPLOADS_DIR.mkdir(exist_ok=True)
STATIC_DIR = FSPath("static")
STATIC_DIR.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
async def root():
    return FileResponse(STATIC_DIR / "index.html")

# Chat history storage
chat_history_store = {}

def get_chat_history(session_id: str):
    return chat_history_store.get(session_id, [])

def add_message_to_history(session_id: str, role: str, text: str):
    if session_id not in chat_history_store:
        chat_history_store[session_id] = []
    chat_history_store[session_id].append({"role": role, "text": text})

def build_gemini_contents(session_id: str, limit: int = 5):
    history = get_chat_history(session_id)[-limit:]
    return [{"role": msg["role"], "parts": [{"text": msg["text"]}]} for msg in history]

# Persona prompt
PERSONA_PROMPT = (
    "You are Leo, a helpful and friendly AI assistant. "
    "You speak clearly, stay concise, and maintain a conversational tone. "
    "You blend warmth with intelligence, avoid being overly formal, "
    "and gently steer the conversation back if the user goes off-topic."
)

# Web search special skill
async def simple_web_search(query: str) -> str:
    url = f"https://api.duckduckgo.com/?q={query}&format=json"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        if resp.status_code == 200:
            data = resp.json()
            abstract = data.get("AbstractText")
            if abstract:
                return abstract
            topics = data.get("RelatedTopics", [])
            if topics:
                first = topics[0]
                if "Text" in first:
                    return first["Text"]
                if "FirstURL" in first:
                    return f"Here's a link: {first['FirstURL']}"
            heading = data.get("Heading")
            if heading:
                return f"I found something about {heading}, but details are limited."
            return "No direct answer found, try refining your query."
        return "Web search service is currently unavailable."

# NewsAPI special skill with URL encoding and logging
async def get_latest_news(topic: str) -> str:
    if not NEWSAPI_KEY:
        return "NewsAPI key not configured; news feature unavailable."
    topic_encoded = urllib.parse.quote_plus(topic)
    url = (
        f"https://newsapi.org/v2/top-headlines?"
        f"q={topic_encoded}&language=en&pageSize=5&apiKey={NEWSAPI_KEY}"
    )
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        logger.info(f"NewsAPI response status: {resp.status_code}, body: {resp.text[:300]}")
        if resp.status_code != 200:
            return "News service is currently unavailable."
        data = resp.json()
        articles = data.get("articles", [])
        if not articles:
            return f"No news found for '{topic}'."
        headlines = [f"- {article['title']}" for article in articles]
        return "Here are the top headlines:\n" + "\n".join(headlines)

# Chat endpoint
@app.post("/agent/chat/{session_id}")
async def chat_with_history(session_id: str = ApiPath(...), file: UploadFile = File(...)):
    # Save uploaded audio
    with tempfile.NamedTemporaryFile(dir=UPLOADS_DIR, suffix=".wav", delete=False) as temp_audio:
        shutil.copyfileobj(file.file, temp_audio)
        temp_path = temp_audio.name
    logger.info(f"Saved uploaded audio to {temp_path}")

    try:
        # Transcribe audio
        transcript = transcriber.transcribe(temp_path)
    except Exception as e:
        os.unlink(temp_path)
        logger.exception("Transcription failed")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
    finally:
        os.unlink(temp_path)

    if transcript.error or not transcript.text or not transcript.text.strip():
        raise HTTPException(status_code=400, detail=f"Transcription error: {transcript.error or 'Empty text'}")

    user_text = transcript.text.strip()
    logger.info(f"Transcript: {user_text}")

    # Special skill: web search
    if user_text.lower().startswith("search:"):
        search_query = user_text[len("search:"):].strip()
        search_result = await simple_web_search(search_query)
        add_message_to_history(session_id, "user", user_text)
        add_message_to_history(session_id, "model", search_result)
        return {"user_text": user_text, "llm_text": search_result, "audio_url": ""}

    # Special skill: latest news
    if user_text.lower().startswith("news:"):
        topic = user_text[len("news:"):].strip()
        news_report = await get_latest_news(topic)
        add_message_to_history(session_id, "user", user_text)
        add_message_to_history(session_id, "model", news_report)
        return {"user_text": user_text, "llm_text": news_report, "audio_url": ""}

    # Normal chat flow: Gemini + Murf
    add_message_to_history(session_id, "user", user_text)

    gemini_endpoint = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
    headers = {"Content-Type": "application/json"}
    params = {"key": GEMINI_API_KEY}
    contents = [{"role": "model", "parts": [{"text": PERSONA_PROMPT}]}] + build_gemini_contents(session_id)
    payload = {"contents": contents}

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(gemini_endpoint, json=payload, headers=headers, params=params)
            if response.status_code != 200:
                content = await response.aread()
                raise HTTPException(status_code=500, detail=f"Gemini API error: {content.decode(errors='ignore')}")
            llm_data = response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini call failed: {str(e)}")

    llm_reply = None
    try:
        candidates = llm_data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts and "text" in parts[0]:
                llm_reply = parts[0]["text"].strip()
    except Exception as e:
        logger.error(f"Failed to extract Gemini reply: {e}")

    if not llm_reply:
        raise HTTPException(status_code=500, detail="LLM reply missing or empty")

    add_message_to_history(session_id, "model", llm_reply)

    # Murf audio generation
    murf_endpoint = "https://api.murf.ai/v1/speech/generate"
    murf_headers = {"api-key": MURF_API_KEY, "Content-Type": "application/json"}

    maxlen = 3000
    chunks = [llm_reply[i:i + maxlen] for i in range(0, len(llm_reply), maxlen)]

    async def generate_murf_audio(chunk):
        async with httpx.AsyncClient(timeout=60) as client:
            murf_payload = {"text": chunk, "voice_id": "en-US-marcus", "audio_format": "mp3"}
            resp = await client.post(murf_endpoint, json=murf_payload, headers=murf_headers)
            data = resp.json()
            url = data.get("audioFile") or data.get("audio_url")
            if not url:
                raise HTTPException(status_code=500, detail="No audio from Murf for chunk")
            return url

    try:
        audio_urls = await asyncio.gather(*(generate_murf_audio(chunk) for chunk in chunks))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Murf call failed: {str(e)}")

    return {"user_text": user_text, "llm_text": llm_reply, "audio_url": audio_urls[0]}
