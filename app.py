from fastapi.responses import FileResponse
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests, os, time

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
You are an AI software agency.
Generate COMPLETE WORKING CODE only.

Include:
- Backend
- Frontend
- Database
- Deployment

Fix bugs automatically.
No explanation.
"""

# ===== MODELS =====
class Data(BaseModel):
    idea: str

class ChatData(BaseModel):
    message: str

# ===== STORAGE =====
memory = {}
projects = []
credits = {"default": 5}
stats = {"users": 1, "requests": 0}
history = []

# ===== GROQ CALL =====
def call_groq(messages):
    res = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "llama3-70b-8192",
            "messages": messages
        }
    )
    return res.json()["choices"][0]["message"]["content"]

# ===== GENERATE (MULTI-AGENT) =====
@app.post("/generate")
def generate(d: Data):

    user = "default"

    if credits.get(user, 0) <= 0:
        return {"error": "No credits 🔒"}

    credits[user] -= 1
    stats["requests"] += 1

    # improve idea
    improved = call_groq([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Improve this idea professionally: {d.idea}"}
    ])

    memory[user] = improved

    # agents
    planner = call_groq([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Analyze: {improved}"}
    ])

    backend = call_groq([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Backend code: {planner}"}
    ])

    frontend = call_groq([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Frontend UI: {planner}"}
    ])

    database = call_groq([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Database: {planner}"}
    ])

    deploy = call_groq([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"AWS deploy: {planner}"}
    ])

    bugfix = call_groq([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Fix bugs: {backend} {frontend}"}
    ])

    optimize = call_groq([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Optimize code: {bugfix}"}
    ])

    business = call_groq([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Monetize this project: {improved}"}
    ])

    final = call_groq([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Combine everything cleanly: {optimize}"}
    ])

    result = {
        "planner": planner,
        "backend": backend,
        "frontend": frontend,
        "database": database,
        "deploy": deploy,
        "bugfix": bugfix,
        "optimize": optimize,
        "business": business,
        "final": final
    }

    projects.append({
        "user": user,
        "idea": improved,
        "time": time.time()
    })

    return result

# ===== CHAT MODE =====
@app.post("/chat")
def chat(d: ChatData):

    global history

    if credits.get("default", 0) <= 0:
        return {"error": "No credits 🔒"}

    credits["default"] -= 1

    history.append({"role": "user", "content": d.message})

    reply = call_groq(
        [{"role": "system", "content": SYSTEM_PROMPT}] + history
    )

    history.append({"role": "assistant", "content": reply})

    return {"reply": reply}

# ===== STATS =====
@app.get("/stats")
def get_stats():
    return stats

# ===== PROJECTS =====
@app.get("/projects")
def get_projects():
    return projects

# ===== HEALTH =====
@app.get("/")
def home():
    return {"msg": "AIMANT AI Running 🚀"}

@app.get("/ui")
def ui():
    return FileResponse("index.html")
