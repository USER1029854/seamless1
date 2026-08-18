#!/usr/bin/env python3
"""Call every zero-arg view function on a contract via its ABI; record results."""
import json, sys, eth, abicall

def read_all(addr, abi):
    out = {}
    for f in abi:
        if f.get("type")!="function": continue
        if f.get("stateMutability") not in ("view","pure"): continue
        if len(f.get("inputs",[]))!=0: continue
        name=f["name"]
        try:
            r=abicall.call_fn(addr, abi, name)
            if "result" in r:
                out[name]=r["result"]
            elif "__revert__" in r:
                out[name]={"revert":str(r["__revert__"])[:80]}
        except Exception as e:
            out[name]={"error":str(e)[:80]}
    return out

def read_one(addr, abi, name, args):
    return abicall.call_fn(addr, abi, name, args)

if __name__=="__main__":
    addr=sys.argv[1]; abipath=sys.argv[2]
    abi=json.load(open(abipath))
    res=read_all(addr, abi)
    print(json.dumps(res, indent=2, default=str))
