from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests, os, time, uuid, zipfile
from threading import Thread

app = FastAPI()

# ===== CORS =====
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== CONFIG =====
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# ===== DATABASE (TEMP MEMORY) =====
users = {}
projects = []
builds = {}
last_request = {}

stats = {
    "users": 0,
    "requests": 0,
    "projects": 0
}

# ===== MODELS =====
class User(BaseModel):
    email: str
    password: str

class Data(BaseModel):
    idea: str
    email: str = "guest"

class BuildRequest(BaseModel):
    idea: str
    email: str = "guest"

# ===== HELPER =====
def check_limit(user):
    now = time.time()
    if user in last_request and now - last_request[user] < 2:
        return False
    last_request[user] = now
    return True

def agent(prompt, input):
    return call_groq([
        {"role": "system", "content": prompt},
        {"role": "user", "content": input}
    ])

def add_log(build_id, msg):
    builds[build_id]["logs"].append(msg)

# ===== GROQ CALL =====
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

            if "error" in data:
                if "rate_limit" in str(data):
                    time.sleep(2)
                    continue
                return f"AI Error: {data['error']['message']}"

            if "choices" not in data:
                return "Invalid AI response"

            return data["choices"][0]["message"]["content"]

        except Exception as e:
            return f"Server Error: {str(e)}"

    return "AI busy, try again"

# ===== AUTH =====
@app.post("/signup")
def signup(u: User):
    if u.email in users:
        return {"error": "User exists"}

    users[u.email] = {
        "password": u.password,
        "credits": 20
    }

    stats["users"] += 1
    return {"msg": "Signup success"}

@app.post("/login")
def login(u: User):
    if u.email in users and users[u.email]["password"] == u.password:
        return {"msg": "Login success"}
    return {"error": "Invalid login"}

# ===== SIMPLE GENERATE =====
@app.post("/generate")
def generate(d: Data):
    user = users.get(d.email, {"credits": 5})

    if not check_limit(d.email):
        return {"error": "Slow down"}

    if user["credits"] <= 0:
        return {"error": "No credits"}

    user["credits"] -= 1
    stats["requests"] += 1

    idea = d.idea

    improved = agent("Improve SaaS idea", idea)
    features = agent("Generate features", improved)
    backend = agent("Generate FastAPI backend", features)
    frontend = agent("Generate modern UI", features)
    deploy = agent("Explain deployment", backend)

    projects.append({
        "user": d.email,
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

# ===== START BUILD =====
@app.post("/start-build")
def start_build(req: BuildRequest):
    build_id = str(uuid.uuid4())

    builds[build_id] = {
        "status": "starting",
        "step": "init",
        "logs": [],
        "data": {}
    }

    Thread(target=run_build, args=(build_id, req.idea, req.email)).start()

    return {"build_id": build_id}

# ===== BUILD PIPELINE =====
def run_build(build_id, idea, email):
    try:
        add_log(build_id, "🚀 Start build")

        builds[build_id]["step"] = "analyzing"
        improved = agent("Improve SaaS idea", idea)
        builds[build_id]["data"]["idea"] = improved
        add_log(build_id, "Idea improved")

        builds[build_id]["step"] = "features"
        features = agent("Generate features", improved)
        builds[build_id]["data"]["features"] = features
        add_log(build_id, "Features ready")

        builds[build_id]["step"] = "backend"
        backend = agent("Generate FastAPI backend", features)
        builds[build_id]["data"]["backend"] = backend
        add_log(build_id, "Backend ready")

        builds[build_id]["step"] = "frontend"
        frontend = agent("Generate modern UI", features)
        builds[build_id]["data"]["frontend"] = frontend
        add_log(build_id, "Frontend ready")

        builds[build_id]["step"] = "deploy"
        deploy = agent("Explain deployment", backend)
        builds[build_id]["data"]["deploy"] = deploy
        add_log(build_id, "Deploy ready")

        save_project(build_id, frontend)

        builds[build_id]["status"] = "completed"
        builds[build_id]["step"] = "done"

        projects.append({
            "user": email,
            "idea": improved,
            "time": time.time()
        })

        stats["projects"] += 1

    except Exception as e:
        builds[build_id]["status"] = "error"
        builds[build_id]["error"] = str(e)

# ===== SAVE FILE =====
def save_project(build_id, code):
    folder = f"projects/{build_id}"
    os.makedirs(folder, exist_ok=True)

    with open(f"{folder}/index.html", "w") as f:
        f.write(code)

# ===== STATUS =====
@app.get("/build-status/{build_id}")
def build_status(build_id: str):
    return builds.get(build_id, {"error": "Not found"})

# ===== DOWNLOAD =====
@app.get("/download/{build_id}")
def download(build_id: str):
    folder = f"projects/{build_id}"
    zip_path = f"{build_id}.zip"

    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for root, dirs, files in os.walk(folder):
            for file in files:
                zipf.write(os.path.join(root, file))

    return FileResponse(zip_path)

# ===== GITHUB PUSH =====
@app.post("/push-github")
def push_github(build_id: str):
    build = builds.get(build_id)

    if not build:
        return {"error": "Invalid build"}

    content = build["data"].get("frontend", "")

    url = "https://api.github.com/repos/YOUR_USERNAME/ai-projects/contents/index.html"

    res = requests.put(
        url,
        headers={"Authorization": f"token {GITHUB_TOKEN}"},
        json={
            "message": "AI Project",
            "content": content.encode("utf-8").decode("latin1")
        }
    )

    return res.json()

# ===== PUBLISH =====
@app.post("/publish")
def publish(build_id: str):
    return {
        "status": "live",
        "url": f"https://ai-{build_id}.onrender.com"
    }

# ===== STATS =====
@app.get("/stats")
def stats_api():
    return stats

# ===== PROJECTS =====
@app.get("/projects")
def project_api():
    return projects

# ===== USER =====
@app.get("/user/{email}")
def user_info(email: str):
    user = users.get(email)
    if not user:
        return {"error": "User not found"}

    return {
        "credits": user["credits"],
        "projects": len(projects)
    }

# ===== UI =====
@app.get("/")
def home():
    return FileResponse("index.html")

@app.get("/builder")
def builder():
    return FileResponse("builder.html")

# ===== RUN =====
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
