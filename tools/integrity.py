#!/usr/bin/env python3
"""Diff embedded OZ (and other upstream) library files against real upstream release tags.
A byte-identical match at any legitimate tag => clean. No match => flag for review."""
import sys, os, hashlib, urllib.request, json

def sha(b): return hashlib.sha256(b).hexdigest()
def norm(b):
    # normalize CRLF->LF and strip trailing whitespace-only differences at EOF
    return b.replace(b"\r\n", b"\n")

def fetch(url):
    try:
        req=urllib.request.Request(url, headers={"User-Agent":"audit/1.0"})
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.read()
    except Exception:
        return None

def check(local_path, repo, rel_path, tags):
    lb = norm(open(local_path,"rb").read())
    lh = sha(lb)
    for t in tags:
        url=f"https://raw.githubusercontent.com/OpenZeppelin/{repo}/{t}/contracts/{rel_path}"
        ub=fetch(url)
        if ub is None: continue
        if sha(norm(ub))==lh:
            return {"file":rel_path,"repo":repo,"status":"IDENTICAL","matched_tag":t,"sha":lh[:16]}
    return {"file":rel_path,"repo":repo,"status":"NO_MATCH","sha":lh[:16]}

if __name__=="__main__":
    print("integrity module")
