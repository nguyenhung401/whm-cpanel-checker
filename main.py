from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import re
import requests
from requests.auth import HTTPBasicAuth
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = FastAPI()

# --- FIX CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # cho phép mọi domain (GitHub Pages, localhost...)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

LINE_RE = re.compile(
    r'^(?:https?://)?(?P<host>[^:/\s]+):(?P<port>\d+):(?P<user>[^:]+):(?P<pwd>.+)$',
    re.IGNORECASE
)

def parse_line(line):
    m = LINE_RE.match(line.strip())
    if not m:
        return None
    return {
        "host": m.group("host"),
        "port": int(m.group("port")),
        "user": m.group("user"),
        "password": m.group("pwd")
    }

def detect_type(port):
    if port in (2087, 2086):
        return "whm"
    if port in (2083, 2082):
        return "cpanel"
    return "cpanel"

def check_whm(host, port, user, pw):
    url = f"https://{host}:{port}/json-api/listaccts?api.version=1"
    try:
        r = requests.get(url, auth=HTTPBasicAuth(user, pw), timeout=8, verify=False)
        if r.status_code == 200 and "data" in r.text:
            return True, "WHM OK"
        return False, f"HTTP {r.status_code}"
    except Exception as e:
        return False, f"ERR: {e}"

def check_cp(host, port, user, pw):
    url = f"https://{host}:{port}/json-api/cpanel?cpanel_jsonapi_version=2&cpanel_jsonapi_module=Lang&cpanel_jsonapi_func=get_version"
    try:
        r = requests.get(url, auth=HTTPBasicAuth(user, pw), timeout=8, verify=False)
        if r.status_code == 200 and ("data" in r.text or "cpanelresult" in r.text):
            return True, "cPanel OK"
        return False, f"HTTP {r.status_code}"
    except Exception as e:
        return False, f"ERR: {e}"

def process_lines(lines):
    results = []

    def worker(line):
        p = parse_line(line)
        if not p:
            return {"line": line, "status": "BAD_FORMAT"}
        host = p["host"]; port = p["port"]
        user = p["user"]; pw = p["password"]

        t = detect_type(port)
        if t == "whm":
            ok, msg = check_whm(host, port, user, pw)
        else:
            ok, msg = check_cp(host, port, user, pw)

        return {
            "line": line,
            "host": host,
            "port": port,
            "user": user,
            "type": t,
            "status": "OK" if ok else "FAIL",
            "message": msg
        }

    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = [ex.submit(worker, ln) for ln in lines]
        for fut in as_completed(futures):
            results.append(fut.result())

    lookup = {res["line"]: res for res in results}
    return [lookup.get(ln, {"line": ln, "status": "ERR"}) for ln in lines]

class ScanRequest(BaseModel):
    text: str

@app.post("/scan")
def scan_file(req: ScanRequest):
    lines = [x.strip() for x in req.text.splitlines() if x.strip()]
    return {"results": process_lines(lines)}

@app.get("/")
def root():
    return {"status": "WHM/cPanel Checker API running"}
