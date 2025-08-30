# 🦁 Voice Agent – Leo  

Leo is a conversational **AI Voice Agent** powered by **FastAPI**, **AssemblyAI**, **Murf AI**, and **Google Gemini**.  
It listens to your speech, transcribes it, generates intelligent responses, and speaks them back — all in real time.  

---

## 🚀 Features  
- 🎙️ **Voice Input & Output** – Speak naturally, Leo responds with AI-generated speech  
- 🤖 **Conversational AI** – Powered by Google Gemini for intelligent responses  
- 📝 **Transcription** – Uses AssemblyAI for accurate speech-to-text  
- 📰 **Special Skills** – Fetches latest news, weather, and more  
- ⚙️ **Custom Config Panel** – Enter your own API keys directly in the UI (no `.env` required)  
- 🌐 **Deployed Online** – Accessible anywhere via browser  

👉 **Live Demo:** [https://voice-agent-leo.onrender.com](https://voice-agent-leo-bewc.onrender.com)  

---

## 🛠️ Tech Stack  
- **Backend:** FastAPI (Python)  
- **Frontend:** HTML, CSS, Vanilla JS  
- **APIs & Services:**  
  - [AssemblyAI](https://www.assemblyai.com/) – Speech-to-Text  
  - [Murf AI](https://murf.ai/) – Text-to-Speech  
  - [Google Gemini](https://ai.google/) – Conversational AI  
  - [NewsAPI](https://newsapi.org/) – News fetching  

---

## 📂 Project Structure
 ```
  Voice-Agent-Leo/
│
├── main.py # FastAPI backend
├── requirements.txt # Python dependencies
├── static/ # Frontend assets (HTML, CSS, JS)
│ ├── index.html
└── README.md # Project documentation
 ```

---

## ⚡ Getting Started  

### 1. Clone the repo  
```bash
git clone https://github.com/DeepakManga22/Voice-Agent-Leo.git
cd Voice-Agent-Leo
 ```
### 2. Install dependencies
```bash
pip install -r requirements.txt
```
### 3. Run locally
```bash
uvicorn main:app --reload
```
Now visit 👉 http://127.0.0.1:8000 in your browser.
### 🔑 API Keys

Leo requires the following API keys (entered via Config Panel in the UI):

**AssemblyAI API Key**

**Murf API Key**

**Google Gemini API Key**

**NewsAPI Key**


## Happy building!
