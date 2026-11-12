import json, os, subprocess, sys, time, urllib.request, urllib.error
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _gh import read_cred, api

REPO = "shengda-demo"
WORK = r"D:\DeepSeek harness\github\shengda"
GIT = r"D:\Git\cmd\git.exe"
PROXY = "http://127.0.0.1:1080"

def mask(text, token):
    return (text or "").replace(token, "***")

def run(args, token, cwd=WORK, check=True):
    env = dict(os.environ)
    env.update({
        "HTTP_PROXY": PROXY, "HTTPS_PROXY": PROXY,
        "GIT_TERMINAL_PROMPT": "0", "GIT_ASKPASS": "echo",
        "GIT_CONFIG_PARAMETERS": "",
    })
    p = subprocess.run(args, cwd=cwd, capture_output=True, text=True, env=env, timeout=300)
    out = mask(p.stdout, token) + mask(p.stderr, token)
    shown = " ".join("URL" if "://" in a else a for a in args[1:6])
    print("$ git %s\n  exit=%d\n  %s" % (shown, p.returncode, out.strip()[:1500]))
    if check and p.returncode != 0:
        raise SystemExit("command failed: %s" % " ".join(args[:3]))
    return p.returncode, out

user, token = read_cred()
print("account:", user)

st, body = api("/repos/%s/%s" % (user, REPO), token=token, user=user)
if st == 404:
    st, body = api("/user/repos", method="POST", token=token, user=user, payload={
        "name": REPO,
        "description": "声搭 · AI短视频配乐助手 — 产品测评交互 Demo",
        "homepage": "https://%s.github.io/%s/" % (user, REPO),
        "private": False,
        "has_issues": False,
        "has_wiki": False,
    })
    print("create repo:", st)
    if st not in (200, 201):
        print(json.dumps(body, ensure_ascii=False)[:500])
        raise SystemExit("repo create failed")
else:
    print("repo exists:", st)

if not os.path.isdir(os.path.join(WORK, ".git")):
    run([GIT, "init", "-b", "main"], token)
run([GIT, "config", "user.name", "Hanqi Yao"], token)
run([GIT, "config", "user.email", "hanqi3@users.noreply.github.com"], token)
run([GIT, "add", "-A"], token)
rc, out = run([GIT, "commit", "-m", "声搭 Demo: single-file interactive prototype"], token, check=False)
if rc != 0 and "nothing to commit" not in out:
    raise SystemExit("commit failed")

url = "https://x-access-token:%s@github.com/%s/%s.git" % (token, user, REPO)
run([GIT, "-c", "http.sslBackend=openssl", "-c", "http.proxy=" + PROXY,
     "-c", "credential.helper=", "push", "-f", url, "HEAD:main"], token)

st, body = api("/repos/%s/%s/pages" % (user, REPO), method="POST", token=token, user=user,
               payload={"source": {"branch": "main", "path": "/"}})
print("enable pages:", st, (json.dumps(body, ensure_ascii=False)[:300] if isinstance(body, dict) else body))

site = "https://%s.github.io/%s/" % (user, REPO)
for i in range(40):
    st, body = api("/repos/%s/%s/pages" % (user, REPO), token=token, user=user)
    status = body.get("status") if isinstance(body, dict) else None
    print("pages status:", st, status)
    if status in ("built", None) and st == 200:
        try:
            req = urllib.request.Request(site, headers={"User-Agent": "dsh-publish"})
            with urllib.request.urlopen(req, timeout=30) as r:
                print("SITE OK", r.status, r.headers.get("Content-Length"), site)
                sys.exit(0)
        except Exception as e:
            print("site not ready:", type(e).__name__, str(e)[:120])
    time.sleep(10)
print("timed out waiting for pages")
