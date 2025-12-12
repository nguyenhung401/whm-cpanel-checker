from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import re
import requests
from requests.auth import HTTPBasicAuth
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = FastAPI()

# ------------------------------
# Serve UI
# ------------------------------
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
def home():
    return FileResponse("index.html")


# ------------------------------
# Checker code
# ------------------------------
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
    port = int(port)
    if port in (2087, 2086): return "whm"
    if port in (2083, 2082): return "cpanel"
    if port == 2222: return "directadmin"
    if port in (8443, 8880): return "plesk"
    if port == 10000: return "webmin"
    if port == 21: return "ftp"
    if port == 22: return "ssh"
    if port in (25, 465, 587, 2525): return "smtp"
    return "unknown"

def check_whm(host, port, user, pw):
    try:
        r = requests.get(
            f"https://{host}:{port}/json-api/listaccts?api.version=1",
            auth=HTTPBasicAuth(user, pw),
            timeout=10,
            verify=False
        )
        return (r.status_code == 200), f"HTTP {r.status_code}"
    except Exception as e:
        return False, f"ERR: {e}"

def check_cp(host, port, user, pw):
    try:
        r = requests.get(
            f"https://{host}:{port}/json-api/cpanel"
            "?cpanel_jsonapi_version=2&cpanel_jsonapi_module=Lang"
            "&cpanel_jsonapi_func=get_version",
            auth=HTTPBasicAuth(user, pw),
            timeout=10,
            verify=False
        )
        return (r.status_code == 200), f"HTTP {r.status_code}"
    except Exception as e:
        return False, f"ERR: {e}"

def process_lines(lines):
    results = []

    def worker(line):
        p = parse_line(line)
        if not p:
            return {"line": line, "status": "BAD_FORMAT"}

        host, port, user, pw = p["host"], p["port"], p["user"], p["password"]
        typ = detect_type(port)

        if typ == "whm":
            ok, msg = check_whm(host, port, user, pw)
        elif typ == "cpanel":
            ok, msg = check_cp(host, port, user, pw)
        else:
            ok, msg = False, "Unsupported type"

        return {
            "line": line,
            "host": host,
            "port": port,
            "user": user,
            "type": typ,
            "status": "OK" if ok else "FAIL",
            "message": msg
        }

    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = [ex.submit(worker, line) for line in lines]
        for f in as_completed(futures):
            results.append(f.result())

    return results

class ScanRequest(BaseModel):
    text: str

@app.post("/scan")
def scan(req: ScanRequest):
    lines = [ln.strip() for ln in req.text.splitlines() if ln.strip()]
    return {"results": process_lines(lines)}
    try:
        url = f"https://{host}:{port}/session_login.cgi"
        r = requests.post(url, data={"user": user, "pass": pw}, timeout=8, verify=False)
        return ("Webmin" in r.text), "Webmin OK" if "Webmin" in r.text else "Webmin FAIL"
    except Exception as e:
        return False, f"ERR: {e}"

def check_ftp(host, port, user, pw):
    try:
        ftp = ftplib.FTP()
        ftp.connect(host, port, timeout=8)
        ftp.login(user, pw)
        ftp.quit()
        return True, "FTP OK"
    except Exception as e:
        return False, f"ERR: {e}"

def check_ssh(host, port, user, pw):
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, port=port, username=user, password=pw, timeout=8)
        client.close()
        return True, "SSH OK"
    except Exception as e:
        return False, f"ERR: {e}"

def check_smtp(host, port, user, pw):
    try:
        server = smtplib.SMTP(host, port, timeout=8)
        server.starttls()
        server.login(user, pw)
        server.quit()
        return True, "SMTP OK"
    except Exception as e:
        return False, f"ERR: {e}"


# ============================
# MAIN PROCESSOR
# ============================
def process_lines(lines):
    results = []

    def worker(line):
        p = parse_line(line)
        if not p:
            return {"line": line, "status": "BAD_FORMAT"}

        host, port, user, pw = p["host"], p["port"], p["user"], p["password"]
        t = detect_type(port)

        mapping = {
            "whm": check_whm,
            "cpanel": check_cp,
            "directadmin": check_directadmin,
            "plesk": check_plesk,
            "webmin": check_webmin,
            "ftp": check_ftp,
            "ssh": check_ssh,
            "smtp": check_smtp
        }

        ok, msg = mapping[t](host, port, user, pw) if t in mapping else (False, "UNKNOWN TYPE")

        return {
            "line": line,
            "host": host,
            "port": port,
            "user": user,
            "type": t,
            "status": "OK" if ok else "FAIL",
            "message": msg
        }

    with ThreadPoolExecutor(max_workers=12) as ex:
        futures = [ex.submit(worker, ln) for ln in lines]
        for fut in as_completed(futures):
            results.append(fut.result())

    return results


# ============================
# API /scan
# ============================
class ScanRequest(BaseModel):
    text: str

@app.post("/scan")
def scan_file(req: ScanRequest):
    lines = [x.strip() for x in req.text.splitlines() if x.strip()]
    return {"results": process_lines(lines)}
  
