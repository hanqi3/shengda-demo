import ctypes, ctypes.wintypes as w, base64, json, os, sys, urllib.request, ssl

class CREDENTIAL(ctypes.Structure):
    _fields_ = [
        ("Flags", w.DWORD), ("Type", w.DWORD), ("TargetName", w.LPWSTR),
        ("Comment", w.LPWSTR), ("LastWritten", w.FILETIME),
        ("CredentialBlobSize", w.DWORD), ("CredentialBlob", ctypes.POINTER(ctypes.c_byte)),
        ("Persist", w.DWORD), ("AttributeCount", w.DWORD), ("Attributes", ctypes.c_void_p),
        ("TargetAlias", w.LPWSTR), ("UserName", w.LPWSTR),
    ]

def read_cred(target="git:https://github.com"):
    adv = ctypes.WinDLL("advapi32", use_last_error=True)
    p = ctypes.c_void_p()
    if not adv.CredReadW(target, 1, 0, ctypes.byref(p)):
        raise RuntimeError("CredRead failed %d" % ctypes.get_last_error())
    c = ctypes.cast(p, ctypes.POINTER(CREDENTIAL)).contents
    blob = ctypes.string_at(c.CredentialBlob, c.CredentialBlobSize).decode("utf-16-le")
    user = c.UserName
    adv.CredFree(p)
    return user, blob

PROXY = "http://127.0.0.1:1080"
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({"https": PROXY, "http": PROXY}))

def api(path, method="GET", payload=None, token=None, user=None):
    url = "https://api.github.com" + path
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", "Basic " + base64.b64encode((user + ":" + token).encode()).decode())
    req.add_header("User-Agent", "dsh-publish")
    req.add_header("Accept", "application/vnd.github+json")
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with OPENER.open(req, timeout=90) as r:
            body = r.read().decode()
            return r.status, (json.loads(body) if body.strip() else None)
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, body

if __name__ == "__main__":
    user, token = read_cred()
    st, me = api("/user", token=token, user=user)
    print("me:", st, me.get("login"), "public_repos=%s" % me.get("public_repos"))
    st, repos = api("/user/repos?per_page=100&sort=updated", token=token, user=user)
    print("repos:", st)
    for r in repos or []:
        print("  -", r["name"], "private" if r["private"] else "public", "pages=" + str(bool(r.get("has_pages"))))
