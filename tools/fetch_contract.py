#!/usr/bin/env python3
"""Fetch a contract's verified source (all Etherscan formats) and save as real files.
Emits a manifest with ABI, compiler, proxy info, and discovered dependency addresses."""
import json, os, re, sys
import eth

OUT = os.environ.get("CONTRACTS_DIR", "contracts")

def _safe(name):
    return re.sub(r'[^A-Za-z0-9_.-]', '_', name)

def parse_sourcecode(sc):
    """Return dict {relpath: content}. Handles single-file, {sources}, and {{standard-json}}."""
    sc = sc.strip()
    if not sc:
        return {}
    # Double-brace standard-json input
    if sc.startswith("{{"):
        obj = json.loads(sc[1:-1])
        srcs = obj.get("sources", {})
        return {p: v.get("content","") for p, v in srcs.items()}
    # Single-brace JSON multi-file (Etherscan sometimes emits {"file.sol":{"content":...}})
    if sc.startswith("{"):
        try:
            obj = json.loads(sc)
            # could be {sources:...} or direct {file:{content}}
            if "sources" in obj and isinstance(obj["sources"], dict):
                return {p: v.get("content","") for p, v in obj["sources"].items()}
            out = {}
            for p, v in obj.items():
                if isinstance(v, dict) and "content" in v:
                    out[p] = v["content"]
            if out:
                return out
        except Exception:
            pass
    # Plain single file
    return {"Contract.sol": sc}

def find_addresses(text):
    """All 20-byte hex addresses in text (checksummed or not), excluding zero."""
    addrs = set()
    for m in re.findall(r'0x[0-9a-fA-F]{40}', text):
        a = m.lower()
        if a != "0x" + "0"*40:
            addrs.add(a)
    return addrs

def fetch(addr, save=True):
    addr = addr.lower()
    d = eth.source(addr)
    res = d.get("result")
    info = {"address": addr, "verified": False, "proxy": False,
            "implementation": None, "name": None, "compiler": None,
            "abi": None, "constructor_args": None, "evm_version": None,
            "optimization": None, "runs": None, "dep_addresses": [], "files": []}
    if not res or not isinstance(res, list):
        info["error"] = str(res)
        return info
    r = res[0]
    name = r.get("ContractName") or ""
    sc = r.get("SourceCode") or ""
    info["name"] = name
    info["compiler"] = r.get("CompilerVersion")
    info["evm_version"] = r.get("EVMVersion")
    info["optimization"] = r.get("OptimizationUsed")
    info["runs"] = r.get("Runs")
    info["constructor_args"] = r.get("ConstructorArguments")
    info["proxy"] = r.get("Proxy") == "1"
    impl = (r.get("Implementation") or "").lower()
    if impl and impl != "0x" + "0"*40:
        info["implementation"] = impl
    abi_raw = r.get("ABI")
    if abi_raw and abi_raw != "Contract source code not verified":
        try: info["abi"] = json.loads(abi_raw)
        except Exception: info["abi"] = None
    if sc and sc != "Contract source code not verified":
        info["verified"] = True
        files = parse_sourcecode(sc)
        base = os.path.join(OUT, f"{_safe(name) or 'Unknown'}_{addr}")
        allsrc = ""
        for relpath, content in files.items():
            allsrc += content + "\n"
            if save:
                # sanitize path components but keep structure
                parts = [_safe(p) for p in relpath.replace("\\","/").split("/") if p not in ("",".","..")]
                fp = os.path.join(base, *parts) if parts else os.path.join(base, "Contract.sol")
                os.makedirs(os.path.dirname(fp), exist_ok=True)
                with open(fp, "w") as f: f.write(content)
                info["files"].append(os.path.relpath(fp, "."))
        info["dep_addresses"] = sorted(find_addresses(allsrc) - {addr})
        if save:
            os.makedirs(base, exist_ok=True)
            with open(os.path.join(base, "_meta.json"), "w") as f:
                meta = {k:v for k,v in info.items() if k != "abi"}
                meta["abi_present"] = info["abi"] is not None
                json.dump(meta, f, indent=2)
            if info["abi"]:
                with open(os.path.join(base, "_abi.json"), "w") as f:
                    json.dump(info["abi"], f, indent=2)
    return info

if __name__ == "__main__":
    for a in sys.argv[1:]:
        i = fetch(a)
        print(json.dumps({k:v for k,v in i.items() if k!="abi"}, indent=2))
