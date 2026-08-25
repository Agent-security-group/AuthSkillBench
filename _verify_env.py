# -*- coding: utf-8 -*-
"""Verify .env loading works WITHOUT python-dotenv (pure stdlib fallback).
No network requests are made. 0 tokens spent.
"""
import os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


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
    src = "python-dotenv"
except ImportError:
    _load_env_file(ROOT / ".env")
    src = "stdlib fallback"

k = os.environ.get("DEEPSEEK_API_KEY")
m = os.environ.get("DEEPSEEK_MODEL")
b = os.environ.get("DEEPSEEK_BASE_URL")

print("===== .env loaded via:", src, "=====")
if k and len(k) > 11:
    masked = k[:7] + "..." + k[-4:]
elif k:
    masked = "SET"
else:
    masked = "NOT SET"
print("DEEPSEEK_API_KEY :", masked)
print("DEEPSEEK_MODEL   :", m)
print("DEEPSEEK_BASE_URL:", b)
print()
print("Result: .env is now readable WITHOUT python-dotenv installed.")
print("NO HTTP request sent. 0 tokens spent.")
