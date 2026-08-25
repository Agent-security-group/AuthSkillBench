# -*- coding: utf-8 -*-
"""Print effective LLM config and optionally ping DeepSeek endpoint."""
from __future__ import annotations
import os, sys, json
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

ROOT = Path(__file__).resolve().parent
def _load_env_file(env_path):
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except Exception:
    _load_env_file(ROOT / ".env")

dk = os.environ.get("DEEPSEEK_API_KEY")
ok_ = os.environ.get("OPENAI_API_KEY")
dm = os.environ.get("DEEPSEEK_MODEL") or "deepseek-chat"
om = os.environ.get("OPENAI_MODEL")
db = os.environ.get("DEEPSEEK_BASE_URL") or "https://api.deepseek.com"
ob = os.environ.get("OPENAI_BASE_URL")

print("===== Effective LLM Config =====")
def mask(k):
    if not k:
        return "NOT SET"
    if len(k) > 11:
        return k[:7] + "..." + k[-4:]
    return "SET"

print("DEEPSEEK_API_KEY :", mask(dk))
print("DEEPSEEK_MODEL   :", dm)
print("DEEPSEEK_BASE_URL:", db)
print("OPENAI_API_KEY   :", mask(ok_))
print("OPENAI_MODEL     :", om or "(not set)")
print("OPENAI_BASE_URL  :", ob or "(not set)")
print()

if dk:
    print("Final choice -> DEEPSEEK /", dm)
    provider = "deepseek"
    api_key, model, base = dk, dm, db
elif ok_:
    print("Final choice -> OPENAI /", (om or "gpt-4o-mini"))
    provider = "openai"
    api_key, model, base = ok_, (om or "gpt-4o-mini"), (ob or "https://api.openai.com/v1")
else:
    print("NO KEY FOUND.")
    print("Set via PowerShell:")
    print('  $env:DEEPSEEK_API_KEY = "sk-XXXXXX"')
    print('  $env:DEEPSEEK_MODEL   = "deepseek-v4-flash"')
    print("Or create file .env in project root with those lines.")
    sys.exit(1)

# --- Minimal API ping ---
print()
print("===== Minimal API ping (1-token completion) =====")
url = base.rstrip("/") + "/chat/completions"
body = json.dumps({
    "model": model,
    "messages": [{"role": "user", "content": "Hi"}],
    "max_tokens": 3,
    "temperature": 0,
}).encode("utf-8")
req = Request(url, data=body, method="POST", headers={
    "Authorization": "Bearer " + api_key,
    "Content-Type": "application/json",
})
try:
    with urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8")
        data = json.loads(raw)
    print("HTTP", resp.status, "OK")
    ch = data["choices"][0]["message"]
    cont = ch.get("content") or "(no-content / tool_calls only)"
    print("Model echo in response:", data.get("model", "(missing)"))
    print("Reply:", cont[:80])
    print()
    print("Key verified. Ready to run live line.")
except HTTPError as e:
    print("HTTP", e.code, "FAIL")
    body_text = ""
    try:
        body_text = e.read().decode("utf-8", errors="replace")
    except Exception:
        pass
    print("Body:", body_text[:500])
    print()
    if e.code == 401:
        print("Invalid API key or key not enabled. Check DEEPSEEK_API_KEY.")
    elif e.code == 404 and "v4-flash" in model.lower():
        print("404: model 'deepseek-v4-flash' not recognized. Try 'deepseek-chat' or 'deepseek-reasoner'.")
    sys.exit(2)
except (URLError, TimeoutError) as e:
    print("Network error:", e)
    print("Can't reach", url)
    sys.exit(3)
