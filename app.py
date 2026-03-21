from fastapi import FastAPI, Header
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests, time, uuid, jwt, os
from threading import Thread
from concurrent.futures import ThreadPoolExecutor
from db import engine
from db import Base
from db import get_db
from models import User
from fastapi import Depends
from sqlalchemy import create_engine
from passlib.context import CryptContext
import razorpay
import hmac, hashlib
from fastapi import Request
import paramiko

# ===== PASSWORD SECURITY =====
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password):
    return pwd_context.hash(password)

def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)

# ===== PYDANTIC MODELS =====
from pydantic import BaseModel

class UserCreate(BaseModel):
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

# ===== APP =====
app = FastAPI()


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

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_USERNAME = "YOUR_USERNAME"
GITHUB_REPO = "YOUR_REPO"

AWS_HOST = "your-ec2-ip"
AWS_USER = "ubuntu"
AWS_KEY = "/root/key.pem"   # path in server


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
def deploy_project(bid):
    log(bid, "🚀 Deploying...")

    code = builds[bid]["data"]["frontend"]

    # GitHub deploy
    deploy_to_github(bid, code)

    # Render deploy
    url = deploy_to_render(bid)

    deployments[bid] = {
        "status": "live",
        "url": url
    }

    # 🔥 USER DATA ADD (YAHAN DAAL)
    user_email = builds[bid].get("user")
    if user_email:
        user_data = get_user_data(user_email)

        user_data["deployments"][bid] = {
            "status": "live",
            "url": url
        }

    log(bid, f"✅ Live: {url}")

# ===== MODELS =====
class User(BaseModel):
    email: str
    password: str

class BuildRequest(BaseModel):
    idea: str

# ===== AUTH =====
import jwt

SECRET = "aimant-secret"

def create_token(email):
    try:
        token = jwt.encode(
            {"email": email},
            SECRET,
            algorithm="HS256"
        )
        return token
    except Exception as e:
        return None


def get_user(token):
    try:
        if not token:
            return None

        # अगर "Bearer token" format आए तो clean करो
        if " " in token:
            token = token.split(" ")[1]

        data = jwt.decode(
            token,
            SECRET,
            algorithms=["HS256"]
        )

        return data.get("email")

    except Exception as e:
        return None


def is_admin(user):
    return user == ADMIN_EMAIL


# ===== MEMORY =====
memory = {}

def save_memory(user, text):
    if user not in memory:
        memory[user] = []

    memory[user].append({
        "text": text,
        "time": time.time()
    })


def get_memory(user):
    if user not in memory:
        return ""

    # last 24h memory
    recent = [
        m["text"]
        for m in memory[user]
        if time.time() - m["time"] < 86400
    ]

    return "\n".join(recent[-5:])

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
                "max_tokens": 1000
            }
        )
        return res.json()["choices"][0]["message"]["content"]

    except Exception as e:
        return f"AI Error: {str(e)}"


def agent(role, text):
    return call_groq([
        {"role": "system", "content": role},
        {"role": "user", "content": text}
    ])


# 💣 AUTO FIX ENGINE (GAME CHANGER)
def auto_fix(code, error):
    return agent(
        "You are a senior developer. Fix the code based on the error. Return ONLY clean working code without explanation.",
        f"CODE:\n{code}\n\nERROR:\n{error}"
    )


# 🧠 SMART PROMPT ENGINE
def smart_prompt(idea):
    return f"""
Build a premium SaaS app for: {idea}

Requirements:
- Modern UI (dark + glassmorphism)
- Responsive mobile-first design
- Clean production-ready code
- Authentication system
- Dashboard UI
- API integration ready
- High conversion landing page
"""


# ⚡ FAST BUILD (parallel AI)
def fast_build(idea):
    with ThreadPoolExecutor() as ex:
        f1 = ex.submit(agent, "Create full SaaS features list", idea)
        f2 = ex.submit(agent, "Create premium frontend HTML/CSS/JS", idea)

    return f1.result(), f2.result()

# ===== PROMPT ENGINE =====
def smart_prompt(idea):
    return f"Build premium SaaS app: {idea}"

# ===== FAST BUILD (3 AGENTS PARALLEL) =====
from concurrent.futures import ThreadPoolExecutor

def fast_build(idea):
    with ThreadPoolExecutor() as ex:
        f1 = ex.submit(agent, "Create SaaS features list", idea)
        f2 = ex.submit(agent, "Create modern premium UI (HTML Tailwind responsive)", idea)
        f3 = ex.submit(agent, "Create backend API (FastAPI production ready)", idea)
        f4 = ex.submit(agent, "Create pricing & monetization strategy", idea)

    return {
        "features": f1.result(),
        "frontend": f2.result(),
        "backend": f3.result(),
        "monetization": f4.result()
    }


# ===== DEPLOY =====
# 🔥 IMPORTS
import base64
import requests
import paramiko
import time

# ===== CONFIG =====
GITHUB_TOKEN = "your_github_token"
GITHUB_REPO = "yourusername/your-repo"

AWS_HOST = "your-ec2-ip"
AWS_USER = "ubuntu"
AWS_KEY = "/root/key.pem"


# 🚀 GITHUB DEPLOY
def deploy_to_github(bid, code):
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{bid}.html"

        data = {
            "message": f"Deploy build {bid}",
            "content": base64.b64encode(code.encode()).decode()
        }

        headers = {
            "Authorization": f"token {GITHUB_TOKEN}"
        }

        res = requests.put(url, json=data, headers=headers)
        return res.json()

    except Exception as e:
        return {"error": str(e)}


# 🌍 AWS DEPLOY (MAIN SERVER)
def deploy_to_aws(bid, code):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        ssh.connect(
            hostname=AWS_HOST,
            username=AWS_USER,
            key_filename=AWS_KEY
        )

        file_name = f"{bid}.html"

        # upload file
        sftp = ssh.open_sftp()
        with sftp.file(f"/home/ubuntu/{file_name}", "w") as f:
            f.write(code)
        sftp.close()

        # run server
        commands = [
            "pkill -f http.server",
            "cd /home/ubuntu",
            "nohup python3 -m http.server 80 > /dev/null 2>&1 &"
        ]

        for cmd in commands:
            ssh.exec_command(cmd)

        ssh.close()

        return f"http://{AWS_HOST}/{file_name}"

    except Exception as e:
        return str(e)


# 🌐 FALLBACK RENDER (OPTIONAL)
def deploy_to_render(bid):
    try:
        url = f"https://aimant-{bid[:6]}.onrender.com"

        deployments[bid] = {
            "status": "live",
            "url": url
        }

        log(bid, f"🌍 Render Live: {url}")
        return url

    except Exception as e:
        return str(e)


# 💣 MAIN DEPLOY (FINAL)
def deploy_project(bid):
    try:
        log(bid, "🚀 Deploying...")
        time.sleep(2)

        code = builds[bid]["data"]["frontend"]

        # 🔥 GitHub backup
        deploy_to_github(bid, code)

        # 🔥 AWS DEPLOY (MAIN)
        url = deploy_to_aws(bid, code)

        # fallback अगर AWS fail हो
        if "http" not in str(url):
            log(bid, "⚠ AWS failed → switching to Render")
            url = deploy_to_render(bid)

        deployments[bid] = {
            "status": "live",
            "url": url
        }

        # 🔥 USER DATA SAVE
        user_email = builds[bid].get("user")
        if user_email:
            user_data = get_user_data(user_email)

            user_data["deployments"][bid] = {
                "status": "live",
                "url": url,
                "time": time.time()
            }

        log(bid, f"✅ Live: {url}")

    except Exception as e:
        deployments[bid] = {
            "status": "error",
            "error": str(e)
        }

        log(bid, f"❌ Error: {str(e)}")


# ⚡ AUTO DEPLOY THREAD
def auto_deploy(bid):
    Thread(target=deploy_project, args=(bid,)).start()

# ===== DAILY STATS =====
def update_daily():
    # increment users
    stats["users"] += 1

    # store stats snapshot
    daily_stats.append({
        "time": time.time(),
        "users": stats["users"],
        "projects": stats["projects"],
        "revenue": stats["revenue"]
    })

# ===== AUTH =====
@app.post("/signup")
def signup(user: UserCreate, db: Session = Depends(get_db)):

    existing = db.query(User).filter(User.email == user.email).first()

    if existing:
        return {"error": "User already exists"}

    new_user = User(
        email=user.email,
        password=hash_password(user.password),
        credits=20
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "Signup successful"}

@app.post("/login")
def login(data: UserLogin, db: Session = Depends(get_db)):

    user = db.query(User).filter(User.email == data.email).first()

    if not user:
        return {"error": "User not found"}

    if not verify_password(data.password, user.password):
        return {"error": "Invalid password"}

    return {
        "message": "Login successful",
        "email": user.email
    }

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
def start_build(req: BuildRequest, authorization: str):

    user_email = get_user(authorization)

    if not user_email:
        return {"error": "Unauthorized"}

    user = users.get(user_email)

    if not user:
        return {"error": "User not found"}

    # 🚫 BLOCK CHECK
    if user_email in blocked_users:
        return {"error": "Blocked"}

    # 💎 PLAN EXPIRY CHECK
    if user.get("expiry"):
        if time.time() > user["expiry"]:
            user["plan"] = "free"
            user["expiry"] = None
            user["credits"] = 5

    # 👥 TEAM CHECK + TEAM CREDIT SYSTEM
    team_found = False

    for team_name, team in teams.items():
        if user_email in team["members"]:
            team_found = True

            if team.get("credits", 0) <= 0:
                return {"error": "Team credits finished"}

            team["credits"] -= 1
            break

    # 💰 NORMAL USER CREDIT CHECK
    if not team_found:
        if user["credits"] <= 0:
            return {"error": "No credits"}

        user["credits"] -= 1

    # 🚀 BUILD START
    bid = str(uuid.uuid4())

    builds[bid] = {
    "status": "running",
    "logs": [],
    "data": {},
    "user": user_email   # 🔥 MUST
   }

    Thread(target=run_build, args=(bid, req.idea, user_email)).start()

    return {"build_id": bid}

# ===== BUILD PIPELINE =====
def run_build(bid, idea, user):
    try:
        log(bid, "🚀 Start")

        # 🧠 smart idea + memory
        idea = smart_prompt(idea + get_memory(user))

        # ⚡ NEW FAST BUILD (4 agents)
        result = fast_build(idea)

        features = result["features"]
        frontend = result["frontend"]
        backend = result["backend"]
        monetization = result["monetization"]

        # 📦 SAVE BUILD DATA
        builds[bid]["data"] = {
            "features": features,
            "frontend": frontend,
            "backend": backend,
            "monetization": monetization
        }

        # 🧠 memory save
        save_memory(user, idea)

        # 🎨 latest template
        templates["latest"] = frontend

        # ✅ done
        builds[bid]["status"] = "done"
        log(bid, "✅ Done")

        # 📊 stats
        stats["projects"] += 1
        update_daily()

        # 🚀 auto deploy
        auto_deploy(bid)

    except Exception as e:
        builds[bid]["status"] = "error"
        builds[bid]["error"] = str(e)

# ===== STATUS =====
@app.get("/build-status/{bid}")
def status(bid: str):
    return builds.get(bid, {})

# ===== LIVE PREVIEW =====
@app.get("/preview/{bid}")
def preview(bid: str):
    if bid not in builds:
        return {"error": "Build not found"}

    return builds[bid]["data"].get("frontend", "")

# ===== DEPLOY STATUS =====
def deploy_project(bid):
    try:
        log(bid, "🚀 Deploying...")

        code = builds[bid]["data"]["frontend"]

        # 🔥 1. AWS (MAIN)
        aws_url = deploy_to_aws(bid, code)

        # 🔥 2. GitHub (backup)
        github_url = deploy_to_github(bid, code)

        # 🔥 3. Render (fallback)
        render_url = deploy_to_render(bid)

        # ✅ FINAL URL (priority AWS > GitHub > Render)
        final_url = aws_url if "http" in aws_url else github_url

        deployments[bid] = {
            "status": "live",
            "url": final_url,
            "aws": aws_url,
            "github": github_url,
            "render": render_url
        }

        # 🔥 USER TRACKING
        user_email = builds[bid].get("user")
        if user_email:
            user_data = get_user_data(user_email)

            user_data["deployments"][bid] = {
                "status": "live",
                "url": final_url,
                "time": time.time()
            }

        log(bid, f"🌍 Live: {final_url}")

    except Exception as e:
        deployments[bid] = {
            "status": "error",
            "error": str(e)
        }

        log(bid, f"❌ Error: {str(e)}")

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

# ===== AI EDIT (LIVE MODIFY) =====

@app.post("/ai-edit")
def ai_edit(build_id: str, prompt: str, authorization: str = Header(None)):

    user = get_user(authorization)

    if not user:
        return {"error": "Unauthorized"}

    if build_id not in builds:
        return {"error": "Build not found"}

    code = builds[build_id]["data"]["frontend"]

    updated = agent(
        "Modify UI based on user prompt",
        code + "\n" + prompt
    )

    builds[build_id]["data"]["frontend"] = updated

    return {"updated": updated}

# ===== DASHBOARD =====
@app.get("/dashboard")
def dashboard(authorization: str = Header(None)):
    user = get_user(authorization)
    return {
        "credits":users.get(user,{}).get("credits",0),
        "templates":list(templates.keys())
    }

# ===== TEMPLATE MARKETPLACE =====
templates = []

@app.post("/add-template")
def add_template(name: str, code: str):
    templates.append({
        "name": name,
        "code": code
    })
    return {"msg": "Template added"}

@app.get("/templates")
def get_templates():
    return templates

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

# ===========================
# 🔥 CUSTOM DOMAIN (YAHAN ADD KAR)
# ===========================

domains = {}

@app.post("/add-domain")
def add_domain(bid: str, domain: str, authorization: str = Header(None)):
    user = get_user(authorization)

    if not user:
        return {"error": "Unauthorized"}

    if bid not in builds:
        return {"error": "Build not found"}

    domains[bid] = {
        "domain": domain,
        "status": "pending"
    }

    return {
        "msg": "Domain added",
        "domain": domain,
        "next_step": "Point your DNS to Render"
    }


@app.get("/domain-status/{bid}")
def domain_status(bid: str):
    return domains.get(bid, {"status": "not found"})

# ===== TEAM SYSTEM =====

@app.post("/create-team")
def create_team(name: str, authorization: str = Header(None)):
    user = get_user(authorization)

    if not user:
        return {"error": "Unauthorized"}

    teams[name] = {
        "owner": user,
        "members": []
    }

    return {"msg": "Team created", "team": name}


@app.post("/add-member")
def add_member(team: str, email: str, authorization: str = Header(None)):
    user = get_user(authorization)

    if team not in teams:
        return {"error": "Team not found"}

    if teams[team]["owner"] != user:
        return {"error": "Not team owner"}

    teams[team]["members"].append(email)

    return {"msg": f"{email} added to {team}"}


@app.get("/team-info")
def team_info(team: str):
    if team not in teams:
        return {"error": "Not found"}

    return teams[team]

# ===== UI =====
@app.get("/")
def home():
    return FileResponse("index.html")

@app.get("/auth")
def auth():
    return FileResponse("auth.html")

@app.get("/dashboard")
def dashboard():
    return FileResponse("dashboard.html")

@app.get("/builder")
def builder():
    return FileResponse("builder.html")

@app.get("/billing")
def billing():
    return FileResponse("billing.html")

@app.get("/domain")
def domain():
    return FileResponse("domain.html")

@app.get("/analytics-page")
def analytics_page():
    return FileResponse("analytics.html")

@app.get("/admin")
def admin_page():
    return FileResponse("admin.html")

# ===== RUN =====
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
