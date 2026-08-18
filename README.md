# Seamless LeverageManager + MorphoLendingAdapter — Audit Source Bundle

Self-contained, audit-ready snapshot of the on-chain trust graph reachable from two
Base (chain **8453**) contracts handed over by the discovery step:

| # | Address | What it is |
|---|---------|-----------|
| **Target 1** | `0x38Ba21C6Bf31dF1b1798FCEd07B4e9b07C5ec3a8` | **LeverageManager** proxy (ERC-1967) over Seamless's bespoke leverage engine |
| **Target 2** | `0x9558b339bb03246c44c57fcee184645dbfab253f` | **MorphoLendingAdapter** (EIP-1167 clone) — per-position custody of collateral/debt on Morpho |

Everything an auditor needs to reason about these two contracts' security is here as
**readable code + recovered behavior + live state**, so the graph can be read without a
block explorer.

## What this system is (one paragraph)

Seamless "Leverage Tokens" are ERC-4626-like shares of a leveraged position. The
**LeverageManager** (Target 1) is the permissionless hub: it mints/redeems shares and routes
rebalances. Each Leverage Token wires to a **LendingAdapter** (Target 2 — holds the position
on a Morpho market) and a **RebalanceAdapter** (runs Dutch auctions to keep the collateral
ratio in band). This deployment has exactly **one** Leverage Token:
`weETH / WETH 17x Leverage Token` — collateral **weETH** (EtherFi, bridged to Base as a
LayerZero OFT), debt **WETH**, on a Morpho Blue market priced by a Morpho-Chainlink oracle
that reads the **weETH/eETH exchange-rate** feed. Upgrade/parameter authority over the whole
system funnels into a **48-hour SeamTimelockController** driven by the SEAM-token DAO
(`SeamGovernorV2`), with a 2-of-3 guardian Safe and a 5-day "long" timelock as its admin.

## How to read this repo

| Path | Contents |
|------|----------|
| `docs/MAP.md` | **Start here.** The full trust graph, both directions, with a diagram and every contract's role + location. |
| `docs/INVENTORY.md` | Machine-generated table of all 35 nodes → name, verified/unverified, file location. |
| `docs/AUTHORITY_AND_STATE.md` | Live authority (who holds every privileged role *right now*) + configuration state (every parameter the code depends on), with flagged observations. |
| `docs/UNRESOLVED.md` | **Prominent list** of what remains genuinely unresolved — mostly off-chain components (Chainlink DON, LayerZero bridge, external governance) — each with the decision it controls and the on-chain evidence that bounds it. |
| `docs/INTEGRITY.md` | Byte-for-byte checks of shared building blocks (OpenZeppelin v5.1.0, Morpho, LayerZero, Safe) against real upstream. |
| `contracts/<Name>_<address>/` | Full verified source of each contract, as real files (as compiled). Proxies resolved to implementations. Each dir has `_meta.json` + `_abi.json`. |
| `artifacts/decompiled/<address>/` | Recovered behavior for the one unverified contract in the path (decompilation, constants, simulation, RECOVERY.md). |
| `artifacts/bytecode/`, `artifacts/constants/` | Raw runtime bytecode + extracted constants for recovered contracts. |
| `state/registry.json` | The resolved graph (nodes, edges, reached-by reasons). |
| `state/live_state.json` | Machine-readable live authority + config + position snapshot. |
| `tools/` | The scripts used to build this bundle (Etherscan V2 + Base RPC + Blockscout fetchers, ABI caller, constants extractor, integrity differ). |

## Provenance / method

- Verified source + ABI: **Etherscan V2** (`getsourcecode`/`getabi`, chainid 8453).
- Live reads (`eth_call`, `eth_getStorageAt`, `eth_getCode`), role/event logs, deployment
  blocks: public **Base RPCs** + **Blockscout** indexed-log API.
- Unverified bytecode recovered with **heimdall-rs v0.8.5** (decompile), a custom
  constant extractor, and unprivileged `eth_call` simulation.
- Snapshot block: see `state/live_state.json` (`block` ~50,121,148, 2026-08-18).

Distinctions are kept explicit throughout: **read** (verified source) vs **recovered**
(decompiled/inferred) vs **assumed** (off-chain, evidenced but not provable from chain).
This bundle deliberately makes **no exploitability judgement** — it exists so the next step
opens onto readable code with nothing that matters left unread, unrecovered, or unnamed.
