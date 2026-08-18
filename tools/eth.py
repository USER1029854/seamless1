#!/usr/bin/env python3
"""Etherscan V2 + Base-RPC + Blockscout helper for Base (chain 8453)."""
import json, sys, time, os, urllib.parse, urllib.request

ETHERSCAN_KEY = os.environ.get("ETHERSCAN_KEY", "R6PYYNEX4CNFAXX4YX3K8W4NXSBGGG4QGJ")
BLOCKSCOUT_KEY = os.environ.get("BLOCKSCOUT_KEY", "proapi_CXlzRYJyLN9T7Uxugw1KTDV51rjzCrMXVSKTfyf5Tn5CUzrqEWYCSWcXQUiKfmNB_fNH9s")
CHAIN = int(os.environ.get("CHAIN", "8453"))
ES = "https://api.etherscan.io/v2/api"
BS = "https://base.blockscout.com"
RPCS = [
    "https://mainnet.base.org",
    "https://base-rpc.publicnode.com",
    "https://1rpc.io/base",
    "https://base.drpc.org",
    "https://base.meowrpc.com",
]
_LAST = [0.0]; _MIN_GAP = 0.21

def _throttle():
    dt = time.time() - _LAST[0]
    if dt < _MIN_GAP: time.sleep(_MIN_GAP - dt)
    _LAST[0] = time.time()

def _get(url, retries=5):
    last = None
    for i in range(retries):
        _throttle()
        try:
            req = urllib.request.Request(url, headers={"User-Agent":"audit/1.0"})
            with urllib.request.urlopen(req, timeout=45) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            last = e; time.sleep(1.2*(i+1))
    raise RuntimeError(f"GET failed: {last}")

def es(params, retries=6):
    params = dict(params); params.setdefault("chainid", CHAIN); params.setdefault("apikey", ETHERSCAN_KEY)
    url = ES + "?" + urllib.parse.urlencode(params)
    for i in range(retries):
        d = _get(url, retries=2)
        msg = str(d.get("result",""))
        if "rate limit" in msg.lower() or "max calls per sec" in msg.lower():
            time.sleep(1.5*(i+1)); continue
        return d
    return d

def source(addr):
    return es({"module":"contract","action":"getsourcecode","address":addr})

def abi(addr):
    return es({"module":"contract","action":"getabi","address":addr})

def rpc(method, params, retries=4):
    payload = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    last = None
    for endpoint in RPCS:
        for i in range(retries):
            _throttle()
            try:
                req = urllib.request.Request(endpoint, data=payload, headers={"Content-Type":"application/json","User-Agent":"audit/1.0"})
                with urllib.request.urlopen(req, timeout=30) as r:
                    d = json.loads(r.read().decode())
                if "result" in d: return d["result"]
                if "error" in d:
                    emsg = str(d["error"]).lower()
                    ecode = d["error"].get("code") if isinstance(d["error"], dict) else None
                    retryable = any(k in emsg for k in ["usage limit","rate limit","limit exceeded","too many","range","block range","payload","exceed","-32005","capacity","timeout","try again"]) or ecode in (-32001,-32005,-32016,-32098,429)
                    if retryable:
                        last = d["error"]; continue
                    # a real revert/logic error: return it (don't rotate endpoints)
                    return {"__error__": d["error"]}
            except Exception as e:
                last = e; time.sleep(0.6*(i+1))
    raise RuntimeError(f"rpc {method} failed on all endpoints: {last}")

def get_code(addr): return rpc("eth_getCode", [addr, "latest"])
def get_storage(addr, slot): return rpc("eth_getStorageAt", [addr, slot, "latest"])
def get_balance(addr): return rpc("eth_getBalance", [addr, "latest"])
def call(to, data, frm=None):
    tx = {"to": to, "data": data}
    if frm: tx["from"] = frm
    return rpc("eth_call", [tx, "latest"])
def block_number(): return rpc("eth_blockNumber", [])

def get_logs(address, topics=None, from_block=0, to_block="latest", chunk=200000):
    """eth_getLogs with endpoint rotation and range chunking."""
    if to_block == "latest":
        to_block = int(block_number(), 16)
    from_block = int(from_block)
    to_block = int(to_block)
    out = []
    start = from_block
    while start <= to_block:
        end = min(start + chunk - 1, to_block)
        params = {"address": address, "fromBlock": hex(start), "toBlock": hex(end)}
        if topics: params["topics"] = topics
        r = rpc("eth_getLogs", [params])
        if isinstance(r, dict) and "__error__" in r:
            # shrink chunk on range errors
            if chunk > 2000:
                chunk = chunk // 4; continue
            raise RuntimeError(f"getLogs failed [{start},{end}]: {r['__error__']}")
        out.extend(r); start = end + 1
    return out

# --- Blockscout ---
def bs_creation(addr):
    return _get(f"{BS}/api/v2/smart-contracts/{addr}", retries=3)
def bs_addr(addr):
    return _get(f"{BS}/api/v2/addresses/{addr}", retries=3)
def bs_source_v1(addr):
    url = f"{BS}/api?module=contract&action=getsourcecode&address={addr}&apikey={BLOCKSCOUT_KEY}"
    return _get(url, retries=3)

if __name__ == "__main__":
    a = sys.argv[1]
    if a == "src": print(json.dumps(source(sys.argv[2]), indent=2))
    elif a == "abi": print(json.dumps(abi(sys.argv[2]), indent=2))
    elif a == "code": print(get_code(sys.argv[2]))
    elif a == "call": print(json.dumps(call(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv)>4 else None), indent=2))
    elif a == "storage": print(get_storage(sys.argv[2], sys.argv[3]))
    elif a == "balance": print(get_balance(sys.argv[2]))
    elif a == "block": print(int(block_number(),16))
    elif a == "bscreation": print(json.dumps(bs_creation(sys.argv[2]), indent=2)[:3000])
