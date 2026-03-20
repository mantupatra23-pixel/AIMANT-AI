from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests, os, hashlib, time
from pymongo import MongoClient

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ENV
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MONGO_URL = os.getenv("MONGO_URL")

client = MongoClient(MONGO_URL)
db = client["ai_saas"]
users = db["users"]
logs = db["logs"]

# Models
class Auth(BaseModel):
    username: str
    password: str

class Generate(BaseModel):
    username: str
    idea: str

# Utils
def hash_pass(p):
    return hashlib.sha256(p.encode()).hexdigest()

def groq(prompt):
    res = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "llama3-70b-8192",
            "messages": [{"role":"user","content":prompt}]
        }
    )
    return res.json()["choices"][0]["message"]["content"]

# AUTH
@app.post("/signup")
def signup(a: Auth):
    if users.find_one({"username": a.username}):
        raise HTTPException(400,"exists")

    users.insert_one({
        "username": a.username,
        "password": hash_pass(a.password),
        "plan":"free",
        "usage":0,
        "created": time.time()
    })
    return {"msg":"ok"}

@app.post("/login")
def login(a: Auth):
    u = users.find_one({"username": a.username})
    if not u: raise HTTPException(404,"no user")
    if u["password"] != hash_pass(a.password):
        raise HTTPException(401,"wrong")
    return {"msg":"ok","plan":u["plan"]}

# PAYMENT SIMULATION
@app.post("/upgrade")
def upgrade(username:str):
    users.update_one({"username":username},{"$set":{"plan":"pro"}})
    return {"msg":"pro activated"}

# MULTI AGENT
def agents(idea):
    planner = groq(f"Break into steps: {idea}")
    backend = groq(f"Generate backend: {planner}")
    frontend = groq(f"Generate frontend: {planner}")
    devops = groq(f"Deployment steps AWS: {planner}")
    debug = groq(f"Fix issues: {backend} {frontend}")
    return planner, backend, frontend, devops, debug

# MAIN
@app.post("/generate")
def generate(g: Generate):

    u = users.find_one({"username": g.username})
    if not u: raise HTTPException(404,"user")

    if u["plan"]=="free" and u["usage"]>=5:
        return {"error":"Upgrade needed"}

    users.update_one({"username":g.username},{"$inc":{"usage":1}})

    planner, backend, frontend, devops, debug = agents(g.idea)

    logs.insert_one({
        "user": g.username,
        "idea": g.idea,
        "time": time.time()
    })

    return {
        "planner": planner,
        "backend": backend,
        "frontend": frontend,
        "devops": devops,
        "final": debug
    }
