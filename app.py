from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests, os, time

app = FastAPI()

# ===== CORS (IMPORTANT) =====
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== CONFIG =====
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# ===== STORAGE =====
credits = {"default": 20}
stats = {"users": 1, "requests": 0, "projects": 0}
projects = []

# ===== DATA MODEL =====
class Data(BaseModel):
    idea: str

# ===== GROQ CALL (SAFE + RETRY) =====
def call_groq(messages):
    for i in range(3):
        try:
            res = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": messages,
                    "max_tokens": 800
                },
                timeout=60
            )

            data = res.json()
            print("GROQ:", data)

            # ❌ API error
            if "error" in data:
                if "rate_limit" in str(data):
                    time.sleep(2)
                    continue
                return f"AI Error: {data['error']['message']}"

            # ❌ invalid response
            if "choices" not in data:
                return f"AI Error: Invalid response {data}"

            return data["choices"][0]["message"]["content"]

        except Exception as e:
            return f"Server Error: {str(e)}"

    return "AI busy, try again 🚀"

# ===== MAIN GENERATE =====
@app.post("/generate")
def generate(d: Data):
    user = "default"

    if credits.get(user, 0) <= 0:
        return {"error": "No credits"}

    credits[user] -= 1
    stats["requests"] += 1

    idea = d.idea

    # STEP 1: IDEA IMPROVE
    improved = call_groq([
        {"role": "system", "content": "Improve this SaaS idea and make it profitable"},
        {"role": "user", "content": idea}
    ])

    # STEP 2: FEATURES
    features = call_groq([
        {"role": "system", "content": "Generate features list"},
        {"role": "user", "content": improved}
    ])

    # STEP 3: BACKEND
    backend = call_groq([
        {"role": "system", "content": "Generate backend using FastAPI"},
        {"role": "user", "content": features}
    ])

    # STEP 4: FRONTEND
    frontend = call_groq([
        {"role": "system", "content": "Generate modern HTML CSS JS UI"},
        {"role": "user", "content": features}
    ])

    # STEP 5: DEPLOY
    deploy = call_groq([
        {"role": "system", "content": "Explain deployment on Render"},
        {"role": "user", "content": backend}
    ])

    # SAVE PROJECT
    projects.append({
        "idea": improved,
        "time": time.time()
    })

    stats["projects"] += 1

    return {
        "idea": improved,
        "features": features,
        "backend": backend,
        "frontend": frontend,
        "deploy": deploy
    }

# ===== STATS =====
@app.get("/stats")
def stats_api():
    return stats

# ===== PROJECTS =====
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

# ===== UI ROUTE =====
@app.get("/builder")
def builder():
    return FileResponse("builder.html")

# ===== LOCAL RUN =====
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
