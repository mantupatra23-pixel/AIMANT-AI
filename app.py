from fastapi.responses import FileResponse
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import requests, os, time

app = FastAPI()

# ===== STATIC FILE SERVE =====
@app.get("/")
def home():
    return FileResponse("index.html")

# ===== CORS =====
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== ENV =====
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# ===== SYSTEM PROMPT =====
SYSTEM_PROMPT = """
You are an elite AI software development agency.

Generate COMPLETE production-ready code.

Include:
- Backend API
- Frontend UI
- Database schema
- Deployment steps

Also:
- Fix bugs automatically
- Optimize code
- Suggest monetization

Return clean structured output.
"""

# ===== MODELS =====
class Data(BaseModel):
    idea: str

class ChatData(BaseModel):
    message: str

# ===== STORAGE =====
history = []
memory = {}
projects = []
credits = {"default": 10}
stats = {
    "users": 1,
    "requests": 0,
    "projects": 0
}

# ===== GROQ CALL =====
def call_groq(messages):
    try:
        res = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama3-70b-8192",
                "messages": messages
            },
            timeout=60
        )
        return res.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"AI Error: {str(e)}"

# ===== GENERATE (MULTI-AGENT) =====
@app.post("/generate")
def generate(d: Data):

    user = "default"

    # credits check
    if credits.get(user, 0) <= 0:
        return {"error": "No credits 🔒 Upgrade required"}

    credits[user] -= 1
    stats["requests"] += 1

    # ===== IDEA IMPROVE =====
    improved = call_groq([
        {"role":"system","content":SYSTEM_PROMPT},
        {"role":"user","content":f"Improve this idea professionally: {d.idea}"}
    ])

    memory[user] = improved

    # ===== MULTI AGENTS =====
    planner = call_groq([
        {"role":"system","content":SYSTEM_PROMPT},
        {"role":"user","content":f"Analyze project deeply: {improved}"}
    ])

    backend = call_groq([
        {"role":"system","content":SYSTEM_PROMPT},
        {"role":"user","content":f"Generate backend API: {planner}"}
    ])

    frontend = call_groq([
        {"role":"system","content":SYSTEM_PROMPT},
        {"role":"user","content":f"Generate frontend UI: {planner}"}
    ])

    database = call_groq([
        {"role":"system","content":SYSTEM_PROMPT},
        {"role":"user","content":f"Design database schema: {planner}"}
    ])

    deploy = call_groq([
        {"role":"system","content":SYSTEM_PROMPT},
        {"role":"user","content":f"AWS deployment steps: {planner}"}
    ])

    bugfix = call_groq([
        {"role":"system","content":SYSTEM_PROMPT},
        {"role":"user","content":f"Fix all bugs in: {backend} {frontend}"}
    ])

    optimize = call_groq([
        {"role":"system","content":SYSTEM_PROMPT},
        {"role":"user","content":f"Optimize performance: {bugfix}"}
    ])

    business = call_groq([
        {"role":"system","content":SYSTEM_PROMPT},
        {"role":"user","content":f"How to monetize this project: {improved}"}
    ])

    final = call_groq([
        {"role":"system","content":SYSTEM_PROMPT},
        {"role":"user","content":f"Combine everything cleanly: {optimize}"}
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

    # ===== SAVE PROJECT =====
    projects.append({
        "user": user,
        "idea": improved,
        "time": time.time()
    })

    stats["projects"] += 1

    return result

# ===== CHAT SYSTEM =====
@app.post("/chat")
def chat(d: ChatData):

    user = "default"

    if credits.get(user, 0) <= 0:
        return {"error":"No credits 🔒"}

    credits[user] -= 1

    history.append({"role":"user","content":d.message})

    reply = call_groq(
        [{"role":"system","content":SYSTEM_PROMPT}] + history
    )

    history.append({"role":"assistant","content":reply})

    return {"reply": reply}

# ===== ANALYTICS =====
@app.get("/stats")
def stats_api():
    return stats

# ===== PROJECT HISTORY =====
@app.get("/projects")
def project_api():
    return projects

# ===== USER INFO =====
@app.get("/user")
def user_info():
    return {
        "credits": credits["default"],
        "projects": len(projects)
    }

# ===== RUN SERVER (LOCAL SAFE) =====
import uvicorn

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
