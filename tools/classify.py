import sys, json, eth
def classify(addr):
    addr=addr.lower()
    code=eth.get_code(addr)
    has=code not in (None,"0x","0x0")
    out={"address":addr,"has_code":has,"code_size":(len(code)-2)//2 if has else 0}
    # EIP-1167 clone?
    if has and code.startswith("0x363d3d373d3d3d363d73"):
        out["clone_impl"]="0x"+code[22:62]
    if has:
        d=eth.source(addr); r=(d.get("result") or [{}])[0]
        out["name"]=r.get("ContractName") or None
        sc=r.get("SourceCode") or ""
        out["verified"]= bool(sc) and sc!="Contract source code not verified"
        out["proxy"]=r.get("Proxy")=="1"
        impl=(r.get("Implementation") or "").lower()
        out["impl"]= impl if impl and impl!="0x"+"0"*40 else None
    return out
if __name__=="__main__":
    for a in sys.argv[1:]:
        print(json.dumps(classify(a)))
