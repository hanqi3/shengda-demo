import ctypes, ctypes.wintypes as w, base64, json, os, sys, urllib.request

class CREDENTIAL(ctypes.Structure):
    _fields_ = [
        ("Flags", w.DWORD),
        ("Type", w.DWORD),
        ("TargetName", w.LPWSTR),
        ("Comment", w.LPWSTR),
        ("LastWritten", w.FILETIME),
        ("CredentialBlobSize", w.DWORD),
        ("CredentialBlob", ctypes.POINTER(ctypes.c_byte)),
        ("Persist", w.DWORD),
        ("AttributeCount", w.DWORD),
        ("Attributes", ctypes.c_void_p),
        ("TargetAlias", w.LPWSTR),
        ("UserName", w.LPWSTR),
    ]

def read_cred(target):
    adv = ctypes.WinDLL("advapi32", use_last_error=True)
    p = ctypes.c_void_p()
    ok = adv.CredReadW(target, 1, 0, ctypes.byref(p))
    if not ok:
        return None, ctypes.get_last_error()
    c = ctypes.cast(p, ctypes.POINTER(CREDENTIAL)).contents
    blob = ctypes.string_at(c.CredentialBlob, c.CredentialBlobSize).decode("utf-16-le")
    user = c.UserName
    adv.CredFree(p)
    return (user, blob), 0

if __name__ == "__main__":
    cred, err = read_cred("git:https://github.com")
    if not cred:
        print("ERR", err)
        sys.exit(1)
    user, tok = cred
    print("vault_user=%r token_len=%d token_prefix=%r" % (user, len(tok), tok[:4]))

    # try API as basic auth
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    print("proxy=%s" % proxy)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({"https": proxy, "http": proxy}) if proxy else urllib.request.ProxyHandler({}))
    req = urllib.request.Request("https://api.github.com/user")
    req.add_header("Authorization", "Basic " + base64.b64encode((user + ":" + tok).encode()).decode())
    req.add_header("User-Agent", "dsh-publish")
    try:
        with opener.open(req, timeout=25) as r:
            data = json.load(r)
            print("api_ok login=%s name=%s public_repos=%s" % (data.get("login"), data.get("name"), data.get("public_repos")))
    except Exception as e:
        print("api_err", type(e).__name__, str(e)[:200])
