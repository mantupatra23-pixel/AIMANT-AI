from fastapi import FastAPI, Header
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests, os, time, uuid, jwt
from threading import Thread
from concurrent.futures import ThreadPoolExecutor

app = FastAPI()

# ===== CONFIG =====
SECRET = "aimant_secret"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ADMIN_EMAIL = "admin@aimant.ai"

# ===== CORS =====
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== STORAGE =====
users = {}
builds = {}
memory = {}
templates = {}
deployments = {}
blocked_users = set()
daily_stats = []

stats = {
    "users": 0,
    "projects": 0,
    "revenue": 0
}

# ===== MODELS =====
class User(BaseModel):
    email: str
    password: str

class BuildRequest(BaseModel):
    idea: str

# ===== AUTH =====
def create_token(email):
    return jwt.encode({"email":email}, SECRET, algorithm="HS256")

def get_user(token):
    try:
        return jwt.decode(token, SECRET, algorithms=["HS256"])["email"]
    except:
        return None

def is_admin(user):
    return user == ADMIN_EMAIL

# ===== MEMORY =====
def save_memory(user, text):
    memory.setdefault(user, []).append(text)

def get_memory(user):
    return "\n".join(memory.get(user, [])[-3:])

# ===== LOG =====
def log(bid, msg):
    builds[bid]["logs"].append(f"{time.strftime('%H:%M:%S')} - {msg}")

# ===== AI =====
def call_groq(messages):
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
            }
        )
        return res.json()["choices"][0]["message"]["content"]
    except:
        return "AI Error"

def agent(role, text):
    return call_groq([
        {"role":"system","content":role},
        {"role":"user","content":text}
    ])

# ===== PROMPT ENGINE =====
def smart_prompt(idea):
    return f"Build premium SaaS app: {idea}"

# ===== FAST BUILD =====
def fast_build(idea):
    with ThreadPoolExecutor() as ex:
        f1 = ex.submit(agent, "Create features", idea)
        f2 = ex.submit(agent, "Create UI", idea)
    return f1.result(), f2.result()

# ===== DEPLOY =====
def deploy_project(bid):
    log(bid, "🚀 Deploying...")
    time.sleep(2)

    url = f"https://aimant-{bid[:6]}.onrender.com"

    deployments[bid] = {"status":"live","url":url}
    log(bid, f"🌍 Live: {url}")

def auto_deploy(bid):
    Thread(target=deploy_project, args=(bid,)).start()

# ===== DAILY STATS =====
def update_daily():
    daily_stats.append({
        "time": time.time(),
        "users": stats["users"],
        "projects": stats["projects"],
        "revenue": stats["revenue"]
    })

# ===== AUTH =====
@app.post("/signup")
def signup(u: User):
    if u.email in users:
        return {"error":"User exists"}

    users[u.email] = {"password":u.password,"credits":5}
    stats["users"] += 1

    return {"token":create_token(u.email)}

@app.post("/login")
def login(u: User):
    if u.email in blocked_users:
        return {"error":"User blocked"}

    if u.email in users and users[u.email]["password"] == u.password:
        return {"token":create_token(u.email)}

    return {"error":"Invalid"}

# ===== BUILD =====
@app.post("/start-build")
def start_build(req: BuildRequest, authorization: str = Header(None)):
    user = get_user(authorization) or "guest"

    if user in blocked_users:
        return {"error":"Blocked"}

    if user != "guest":
        if users[user]["credits"] <= 0:
            return {"error":"No credits"}
        users[user]["credits"] -= 1

    bid = str(uuid.uuid4())

    builds[bid] = {"status":"running","logs":[],"data":{}}

    Thread(target=run_build, args=(bid, req.idea, user)).start()

    return {"build_id":bid}

# ===== BUILD PIPELINE =====
def run_build(bid, idea, user):
    try:
        log(bid,"🚀 Start")

        idea = smart_prompt(idea + get_memory(user))

        features, frontend = fast_build(idea)
        backend = agent("Create backend", features)
        monetization = agent("Create pricing", idea)

        builds[bid]["data"] = {
            "features":features,
            "frontend":frontend,
            "backend":backend,
            "monetization":monetization
        }

        save_memory(user, idea)
        templates["latest"] = frontend

        builds[bid]["status"]="done"
        log(bid,"✅ Done")

        stats["projects"] += 1
        update_daily()

        auto_deploy(bid)

    except Exception as e:
        builds[bid]["status"]="error"
        builds[bid]["error"]=str(e)

# ===== STATUS =====
@app.get("/build-status/{bid}")
def status(bid: str):
    return builds.get(bid, {})

# ===== DEPLOY STATUS =====
@app.get("/deploy-status/{bid}")
def deploy_status(bid: str):
    return deployments.get(bid, {"status":"pending"})

# ===== DOWNLOAD =====
@app.get("/download/{bid}")
def download(bid: str):
    file = f"{bid}.html"
    with open(file,"w") as f:
        f.write(builds[bid]["data"]["frontend"])
    return FileResponse(file)

# ===== CHAT =====
@app.post("/chat")
def chat(build_id: str, message: str):
    code = builds[build_id]["data"]["frontend"]
    updated = agent("Modify UI", code + "\n" + message)
    return {"updated":updated}

# ===== DASHBOARD =====
@app.get("/dashboard")
def dashboard(authorization: str = Header(None)):
    user = get_user(authorization)
    return {
        "credits":users.get(user,{}).get("credits",0),
        "templates":list(templates.keys())
    }

# ===== ADMIN =====
@app.post("/admin/block")
def block_user(email: str, authorization: str = Header(None)):
    if not is_admin(get_user(authorization)):
        return {"error":"Not admin"}

    blocked_users.add(email)
    return {"msg":"Blocked"}

@app.post("/admin/unblock")
def unblock_user(email: str, authorization: str = Header(None)):
    if not is_admin(get_user(authorization)):
        return {"error":"Not admin"}

    blocked_users.discard(email)
    return {"msg":"Unblocked"}

@app.get("/admin-users")
def admin_users():
    return [{"email":e,"credits":d["credits"]} for e,d in users.items()]

@app.get("/admin-analytics")
def analytics():
    return {
        "users":stats["users"],
        "projects":stats["projects"],
        "revenue":stats["revenue"],
        "builds":len(builds)
    }

@app.get("/admin-graph")
def graph():
    return daily_stats

@app.get("/admin-secure")
def admin_secure(authorization: str = Header(None)):
    user = get_user(authorization)

    if not is_admin(user):
        return {"error":"Access denied"}

    return {
        "users":users,
        "blocked":list(blocked_users)
    }

# ===== UI =====
@app.get("/")
def home():
    return FileResponse("index.html")

@app.get("/builder")
def builder():
    return FileResponse("builder.html")

@app.get("/admin")
def admin_ui():
    return FileResponse("admin.html")

@app.get("/landing")
def landing():
    return FileResponse("landing.html")

# ===== RUN =====
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
