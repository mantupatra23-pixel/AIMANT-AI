from fastapi import FastAPI, Header
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests, time, uuid, jwt, os
from threading import Thread
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy.orm import Session
from db import engine, Base, get_db
from models import User
from fastapi import Depends
from passlib.context import CryptContext
import razorpay
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
import hmac, hashlib
from fastapi import Request

# ===== APP =====
app = FastAPI()

# ===== SECURITY =====
pwd_context = CryptContext(schemes=["bcrypt"], depre>

def hash_password(password):
    return pwd_context.hash(password)

def verify_password(password, hashed):
    return pwd_context.verify(password, hashed)

# ===== DATABASE =====
DATABASE_URL = "postgresql://user:pass@host/db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()

# 👇 YAHI ADD KAR
Base.metadata.create_all(bind=engine)

# ===== CONFIG =====
SECRET = "aimant_secret"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ADMIN_EMAIL = "admin@aimant.ai"

RAZORPAY_KEY = "rzp_test_ABC123XYZ"
RAZORPAY_SECRET = "your_secret_key_here"

client = razorpay.Client(auth=(RAZORPAY_KEY, RAZORPAY_SECRET))

WEBHOOK_SECRET = "your_webhook_secret"

# ===== PLANS =====
plans = {
    "free": 5,
    "pro": 50,
    "premium": 200
}

# ✅ YAHAN FUNCTION
def check_plan(user):
    if "expiry" in user and time.time() > user["expiry"]:
        user["plan"] = "free"
        user["credits"] = 5


# ===== CORS =====
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== STORAGE =====
User signup → DB save → token generate
User login → DB check → token return
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
def signup(u: UserModel, db: Session = Depends(get_db)):

    # check existing user
    existing = db.query(User).filter(User.email == u.email).first()
    if existing:
        return {"error": "User exists"}

    # 🔐 password hash yaha use hoga
    new_user = User(
        email=u.email,
        password=hash_password(u.password),
        credits=20
    )

    db.add(new_user)
    db.commit()

    return {"msg": "Signup success"}

@app.post("/login")
def login(u: User):
    user = users.get(u.email)

    if not user:
        return {"error": "User not found"}

    if u.email in blocked_users:
        return {"error": "Blocked"}

    # 💎 PLAN EXPIRY CHECK (CORRECT)
    if user.get("expiry"):
        if time.time() > user["expiry"]:
            user["plan"] = "free"
            user["expiry"] = None

    # 🔐 PASSWORD CHECK (HASH FIX)
    if verify_password(u.password, user["password"]):
        return {"token": create_token(u.email)}

    return {"error": "Invalid"}

# ===== PAYMENT APIs =====
@app.post("/create-order")
def create_order(amount: int):
    order = client.order.create({
        "amount": amount * 100,
        "currency": "INR"
    })
    return order

@app.post("/verify-payment")
def verify_payment(data: dict):
    try:
        client.utility.verify_payment_signature({
            "razorpay_order_id": data["order_id"],
            "razorpay_payment_id": data["payment_id"],
            "razorpay_signature": data["signature"]
        })

        user = data.get("email")

        if user not in users:
            return {"error": "User not found"}

        credits = data.get("amount", 0) // 10
        users[user]["credits"] += credits

        # 💎 PLAN LOGIC
        amount = data.get("amount", 0)

        if amount == 99:
            users[user]["plan"] = "pro"
        elif amount == 299:
            users[user]["plan"] = "premium"

        users[user]["expiry"] = time.time() + 30*24*3600

        return {
            "msg": "Payment success",
            "credits": users[user]["credits"],
            "plan": users[user].get("plan")
        }

    except Exception as e:
        return {"error": "Payment failed"}

# ===== PAYMENT / WEBHOOK =====
@app.post("/webhook")
async def webhook(request: Request):

    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature")

    expected = hmac.new(
        WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256
    ).hexdigest()

    if expected != signature:
        return {"error": "Invalid signature"}

    data = await request.json()

    if data["event"] == "payment.captured":

        email = data["payload"]["payment"]["entity"]["notes"]["email"]
        amount = data["payload"]["payment"]["entity"]["amount"] // 100

        if email in users:
            users[email]["credits"] += amount // 10

    return {"status": "ok"}

# ===== BUILD =====
@app.post("/start-build")
def start_build(req: BuildRequest, authorization: str = Header(None)):

    user_email = get_user(authorization)

    if not user_email:
        return {"error":"Unauthorized"}

    user = users.get(user_email)

    if not user:
        return {"error":"User not found"}

    # 🚫 BLOCK CHECK
    if user_email in blocked_users:
        return {"error":"Blocked"}

    # 🔥 EXPIRY CHECK (YAHAN ADD KARNA HAI)
    if "expiry" in user and time.time() > user["expiry"]:
        user["plan"] = "free"
        user["credits"] = 5

    # 💰 CREDIT CHECK
    if user["credits"] <= 0:
        return {"error":"No credits"}

    user["credits"] -= 1

    # 👇 SAME FLOW CONTINUE
    bid = str(uuid.uuid4())

    builds[bid] = {"status":"running","logs":[],"data":{}}

    Thread(target=run_build, args=(bid, req.idea, user_email)).start()

    return {"build_id": bid}

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
    user = get_user(authorization)

    if not is_admin(user):
        return {"error": "Not admin"}

    blocked_users.add(email)
    return {"msg": f"{email} blocked"}


@app.post("/admin/unblock")
def unblock_user(email: str, authorization: str = Header(None)):
    user = get_user(authorization)

    if not is_admin(user):
        return {"error": "Not admin"}

    blocked_users.discard(email)
    return {"msg": f"{email} unblocked"}


# 💎 NEW: SET PLAN (MAIN FEATURE)
@app.post("/admin/set-plan")
def set_plan(email: str, plan: str, days: int, authorization: str = Header(None)):

    admin = get_user(authorization)

    if not is_admin(admin):
        return {"error": "Not admin"}

    if email not in users:
        return {"error": "User not found"}

    users[email]["plan"] = plan
    users[email]["expiry"] = time.time() + days * 24 * 3600

    return {
        "msg": "Plan updated",
        "user": email,
        "plan": plan,
        "days": days
    }


@app.get("/admin-users")
def admin_users(authorization: str = Header(None)):
    user = get_user(authorization)

    if not is_admin(user):
        return {"error": "Not admin"}

    return [
        {
            "email": e,
            "credits": d.get("credits", 0),
            "plan": d.get("plan", "free"),
            "expiry": d.get("expiry")
        }
        for e, d in users.items()
    ]


@app.get("/admin-analytics")
def analytics(authorization: str = Header(None)):
    user = get_user(authorization)

    if not is_admin(user):
        return {"error": "Not admin"}

    return {
        "users": len(users),
        "projects": len(builds),
        "revenue": stats.get("revenue", 0),
        "active_builds": len(builds)
    }


@app.get("/admin-secure")
def admin_secure(authorization: str = Header(None)):
    user = get_user(authorization)

    if not is_admin(user):
        return {"error": "Access denied"}

    return {
        "users": users,
        "blocked": list(blocked_users)
    }

# ===== UI =====
@app.get("/")
def home():
    return FileResponse("index.html")

@app.get("/builder")
def builder():
    return FileResponse("builder.html")

@app.get("/landing")
def landing():
    return FileResponse("landing.html")

@app.get("/admin")
def admin_page():
    return FileResponse("admin.html")

# ===== RUN =====
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
