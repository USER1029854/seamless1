#!/usr/bin/env python3
"""BFS graph resolver. Maintains state/registry.json with all nodes + edges."""
import json, os, sys, eth, fetch_contract as fc, classify as cl

REG_PATH = "/home/user/seamless1/state/registry.json"

def load():
    if os.path.exists(REG_PATH):
        return json.load(open(REG_PATH))
    return {"nodes": {}, "notes": {}}

def save(reg):
    os.makedirs(os.path.dirname(REG_PATH), exist_ok=True)
    json.dump(reg, open(REG_PATH,"w"), indent=2, sort_keys=True)

def process(addr, reg, label=None, reason=None):
    addr = addr.lower()
    node = reg["nodes"].get(addr, {})
    c = cl.classify(addr)
    node.update({k:c.get(k) for k in ["has_code","code_size","verified","name","proxy","impl","clone_impl"]})
    if label: node["label"] = label
    if reason: node.setdefault("reached_by", reason)
    node["address"] = addr
    # save source if verified
    if c.get("verified"):
        info = fc.fetch(addr)
        node["dir"] = f"contracts/{(info['name'] or 'Unknown')}_{addr}"
        node["compiler"] = info.get("compiler")
        node["dep_addresses"] = info.get("dep_addresses", [])
    reg["nodes"][addr] = node
    # implementation/clone targets to follow
    nxt = []
    if node.get("impl"): nxt.append((node["impl"], f"implementation of {addr}"))
    if node.get("clone_impl"): nxt.append((node["clone_impl"], f"EIP1167 impl of {addr}"))
    return nxt

if __name__ == "__main__":
    reg = load()
    for a in sys.argv[1:]:
        for nx,rs in process(a, reg):
            print("  -> follow", nx, rs)
    save(reg)
    print("registry nodes:", len(reg["nodes"]))
