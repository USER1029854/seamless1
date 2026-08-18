import re, os, sys, glob

# Seamless-authored implementation contracts actually running on-chain
IMPLS = {
 "LeverageManager": "contracts/LeverageManager_0xfe9101349354e278970489f935a54905de2e1856/src",
 "MorphoLendingAdapter": "contracts/MorphoLendingAdapter_0x585cc1c8af5c8ad79c64ac66d264590a3ff65c51/src",
 "RebalanceAdapter": "contracts/RebalanceAdapter_0xd923b2522e1f369e207d151cfe6a1bcd8ec24912/src",
 "LeverageToken": "contracts/LeverageToken_0x603da735780e6bc7d04f3fb85c26dcccd4ff0a82/src",
 "BeaconProxyFactory": "contracts/BeaconProxyFactory_0xe0b2e40edeb53b96c923381509a25a615c1abe57/src",
}
# only the concrete contract sources, not interfaces
SKIP_DIR = "/interfaces/"

fnre = re.compile(r'function\s+(\w+)\s*\(([^)]*)\)\s*([^{;]*)', re.S)

for label, base in IMPLS.items():
    print(f"\n########## {label}  ({base})")
    for f in sorted(glob.glob(base+"/**/*.sol", recursive=True)):
        if SKIP_DIR in f: continue
        src = open(f).read()
        # strip comments
        s = re.sub(r'//[^\n]*','',src); s = re.sub(r'/\*.*?\*/','',s,flags=re.S)
        hits=[]
        for m in fnre.finditer(s):
            name, args, mods = m.group(1), m.group(2), m.group(3)
            mods_flat = " ".join(mods.split())
            if 'external' in mods_flat or 'public' in mods_flat:
                vis = 'external' if 'external' in mods_flat else 'public'
                mut = 'view' if ' view' in mods_flat else ('pure' if ' pure' in mods_flat else 'STATE')
                guard = []
                for g in ['onlyRole','onlyOwner','onlyLeverageManager','initializer','reinitializer','nonReentrant','onlyInitializing']:
                    if g in mods_flat: guard.append(g)
                hits.append((name, vis, mut, ",".join(guard) or "-", " ".join(args.split())[:60]))
        # fallback/receive
        for kw in ['fallback','receive']:
            if re.search(r'\b'+kw+r'\s*\(\s*\)', s): hits.append((kw,'external','STATE','-',''))
        if hits:
            print(f"  -- {os.path.basename(f)}")
            for n,v,mu,g,a in hits:
                print(f"     {n:42} {v:8} {mu:5} guard={g:26} ({a})")
