from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests, os, subprocess, time

app = FastAPI()

# ===== CORS =====
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# ===== SYSTEM PROMPT =====
SYSTEM_PROMPT = """
You are an autonomous AI software development agency.

You ONLY generate COMPLETE WORKING CODE.

You must:
- Build backend
- Build frontend
- Add database
- Add deployment

Also:
- Detect bugs
- Fix bugs automatically
- Return clean code

Format:
1. Overview
2. Folder Structure
3. Backend Code
4. Frontend Code
5. Database
6. Deployment
"""

# ===== MODEL =====
class Data(BaseModel):
    idea: str

# ===== MEMORY / CACHE / USAGE =====
memory = {}
cache = {}
usage = {}

# ===== GROQ CALL =====
def call_groq(prompt):
    try:
        res = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama3-70b-8192",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ]
            },
            timeout=60
        )
        return res.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Error: {str(e)}"

# ===== TEMPLATE BOOST =====
def template_boost(idea):
    i = idea.lower()
    if "salon" in i:
        return idea + " with booking system, pricing, admin panel"
    if "gym" in i:
        return idea + " with membership system, trainer booking"
    if "clinic" in i:
        return idea + " with appointment system and patient records"
    return idea

# ===== MAIN =====
@app.post("/generate")
def generate(d: Data):

    user = "default"

    # usage limit
    usage[user] = usage.get(user, 0) + 1
    if usage[user] > 5:
        return {"error": "Upgrade required 🔒"}

    idea = template_boost(d.idea)

    # cache check
    if idea in cache:
        return cache[idea]

    memory[user] = idea

    # ===== MULTI AGENTS =====
    planner = call_groq(f"Analyze project deeply: {idea}")

    backend = call_groq(f"Generate full backend code: {planner}")

    frontend = call_groq(f"Generate full frontend UI: {planner}")

    database = call_groq(f"Design database schema: {planner}")

    deploy = call_groq(f"Give AWS deployment steps: {planner}")

    bugfix = call_groq(f"Find and fix all bugs in: {backend} {frontend}")

    final = call_groq(f"Combine everything cleanly: {bugfix}")

    result = {
        "planner": planner,
        "backend": backend,
        "frontend": frontend,
        "database": database,
        "deploy": deploy,
        "bugfix": bugfix,
        "final": final
    }

    cache[idea] = result

    return result

# ===== HEALTH CHECK =====
@app.get("/")
def home():
    return {"msg": "AI Builder Bot Running 🚀"}

# ===== GITHUB PUSH =====
@app.get("/push")
def push_code():
    try:
        subprocess.run(["git","add","."], check=True)
        subprocess.run(["git","commit","-m","🚀 Auto update"], check=True)
        subprocess.run(["git","push"], check=True)
        return {"msg": "Pushed to GitHub 🚀"}
    except Exception as e:
        return {"msg": f"Push failed: {str(e)}"}
