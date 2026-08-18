#!/usr/bin/env python3
"""Extract embedded constants from EVM runtime bytecode: PUSH20 (addresses),
PUSH32 (hashes/keys/selectors-in-words), 4-byte selectors, and ASCII strings."""
import sys, re

def parse(code):
    code = code[2:] if code.startswith("0x") else code
    b = bytes.fromhex(code)
    # strip trailing CBOR metadata (ipfs/solc) if present
    i = 0; n = len(b)
    push20=[]; push32=[]; other_push=[]
    while i < n:
        op = b[i]
        if 0x60 <= op <= 0x7f:  # PUSH1..PUSH32
            ln = op - 0x5f
            val = b[i+1:i+1+ln]
            if ln == 20:
                push20.append("0x"+val.hex())
            elif ln == 32:
                push32.append("0x"+val.hex())
            i += 1 + ln
        else:
            i += 1
    # ascii strings (printable runs >=3)
    strings = sorted(set(m.decode('ascii',errors='ignore') for m in re.findall(rb'[\x20-\x7e]{3,}', b)))
    return {"push20":sorted(set(push20)), "push32":sorted(set(push32)), "strings":strings}

if __name__=="__main__":
    code=open(sys.argv[1]).read().strip() if len(sys.argv)>1 and not sys.argv[1].startswith("0x") else sys.argv[1]
    r=parse(code)
    import json; print(json.dumps(r, indent=2))
