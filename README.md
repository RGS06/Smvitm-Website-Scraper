# 🎓 SMVITM College Chatbot (RAG-Based)

Welcome to the **SMVITM Virtual Assistant**, a professional AI-powered chatbot designed for Shri Madhwa Vadiraja Institute of Technology and Management. This project uses **RAG (Retrieval-Augmented Generation)** to provide accurate, website-sourced answers to queries about the college, admissions, departments, and more.

## ✨ Key Features
- **🌐 Intelligent Scraper**: Crawls the entire college website to gather up-to-date information.
- **🧠 Accurate RAG Pipeline**: Uses Gemini 1.5 Flash and a custom keyword-retrieval system for precise answers.
- **💎 Premium UI**: A sleek, dark-mode chat interface with glassmorphism and smooth animations.
- **⚡ Fast Responses**: Optimized for accuracy and speed.

## 🛠️ Project Structure
- `backend/`: FastAPI server handling the logic.
- `frontend/`: Modern chat interface (Glassmorphism design).
- `data/`: Scraped content from the website.
- `scraper.py`: The web crawler.
- `process_data.py`: Data cleaning and processing.

## 🚀 How to Run

### 1. Requirements
Ensure you have the virtual environment activated and dependencies installed:
```powershell
.\venv\Scripts\activate
# Dependencies are already installed in your environment!
```

### 2. Start the Backend
The backend serves both the API and the Frontend:
```powershell
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### 3. Open the Chatbot
Visit the following URL in your browser:
**[http://127.0.0.1:8000/static/index.html](http://127.0.0.1:8000/static/index.html)**

## 💬 Queries to Try
- "What branches are offered in this college?"
- "How can I contact the admission officer?"
- "Tell me about the Computer Science department."
- "What are the rules and regulations for students?"

---
*Built for College Chatbot Project.*
