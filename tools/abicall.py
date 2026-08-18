#!/usr/bin/env python3
"""Minimal ABI encoder/decoder + on-chain caller using eth.py RPC."""
import json, sys, re
from Crypto.Hash import keccak
import eth

def kec(s):
    k = keccak.new(digest_bits=256); k.update(s.encode()); return k.digest()

def _canon(t):
    # normalize tuple types recursively for signature
    return t

def type_sig(inp):
    t = inp["type"]
    if t.startswith("tuple"):
        comps = ",".join(type_sig(c) for c in inp.get("components", []))
        return "(" + comps + ")" + t[len("tuple"):]
    return t

def selector(fn):
    args = ",".join(type_sig(i) for i in fn.get("inputs", []))
    sig = f'{fn["name"]}({args})'
    return kec(sig)[:4], sig

def enc_arg(typ, val):
    if typ == "address":
        return bytes.fromhex(f"{int(val,16):040x}").rjust(32, b'\0')
    if typ.startswith("uint") or typ.startswith("int"):
        return int(val).to_bytes(32, "big", signed=typ.startswith("int"))
    if typ == "bool":
        return (1 if val else 0).to_bytes(32, "big")
    if typ.startswith("bytes") and len(typ) > 5:  # bytesN
        b = bytes.fromhex(val[2:] if isinstance(val,str) and val.startswith("0x") else val)
        return b.ljust(32, b'\0')
    raise ValueError(f"enc unsupported {typ}")

def encode_call(fn, args):
    sel, sig = selector(fn)
    data = sel
    # only static args supported (address/uint/bool/bytesN)
    for i, a in zip(fn.get("inputs", []), args):
        data += enc_arg(i["type"], a)
    return "0x" + data.hex(), sig

def _dec_static(typ, word):
    if typ == "address":
        return "0x" + word[12:].hex()
    if typ == "bool":
        return int.from_bytes(word, "big") != 0
    if typ.startswith("uint"):
        return int.from_bytes(word, "big")
    if typ.startswith("int"):
        return int.from_bytes(word, "big", signed=True)
    if typ.startswith("bytes"):
        return "0x" + word.hex()
    return "0x" + word.hex()

def decode_outputs(outputs, raw):
    """Decode return data. Handles flat static outputs and a single/flat tuple of static types.
    Returns list. For dynamic types returns raw hex fallback."""
    if raw is None: return None
    if isinstance(raw, dict) and "__error__" in raw: return raw
    b = bytes.fromhex(raw[2:]) if raw.startswith("0x") else bytes.fromhex(raw)
    if len(b) == 0: return []
    words = [b[i:i+32] for i in range(0, len(b), 32)]
    # flatten one level of tuple
    flat = []
    for o in outputs:
        if o["type"].startswith("tuple"):
            for c in o["components"]:
                flat.append(c)
        else:
            flat.append(o)
    out = []
    # naive: assume all static, consume in order
    try:
        for idx, o in enumerate(flat):
            t = o["type"]
            if t == "string" or t == "bytes" or t.endswith("[]"):
                out.append({"__dynamic__": raw}); continue
            out.append(_dec_static(t, words[idx]))
    except Exception:
        return {"__raw__": raw}
    return out

def call_fn(addr, abi, name, args=None, frm=None):
    args = args or []
    fn = None
    for f in abi:
        if f.get("type") == "function" and f.get("name") == name and len(f.get("inputs",[])) == len(args):
            fn = f; break
    if not fn:
        return {"__error__": f"fn {name} not found"}
    data, sig = encode_call(fn, args)
    raw = eth.call(addr, data, frm)
    if isinstance(raw, dict) and "__error__" in raw:
        return {"__revert__": raw["__error__"], "sig": sig}
    return {"result": decode_outputs(fn.get("outputs",[]), raw), "sig": sig, "raw": raw}

def selector_of(sig):
    return "0x" + kec(sig)[:4].hex()

if __name__ == "__main__":
    # abicall.py <addr> <abi.json> <fnname> [args...]
    addr = sys.argv[1]; abi = json.load(open(sys.argv[2])); name = sys.argv[3]
    args = sys.argv[4:]
    print(json.dumps(call_fn(addr, abi, name, args), indent=2, default=str))
