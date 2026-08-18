# Unresolved & Off-Chain Components

Everything with on-chain code in the graph is **read (verified) or recovered**. Nothing in the
value path is left as an opaque blob. What remains genuinely unresolvable from chain state is
listed here, each with **the decision it controls**, **what goes wrong if it decides wrongly or
is compromised**, and **the on-chain evidence that bounds it**.

There is **no unread or un-recovered contract** in the path. The one unverified contract (weETH
ProxyAdmin) is fully recovered — see the bottom of this file.

---

## Off-chain components in the trust path (cannot be resolved as contracts)

### U1 — Chainlink weETH/eETH OCR2 oracle DON  *(highest-impact off-chain trust)*
- **Where:** market oracle `0xce629400` → feed `0x35e9d700` → underlying
  `AccessControlledOCR2Aggregator` `0x764a8f2f`.
- **Decision it controls:** the weETH/eETH exchange rate, i.e. the price of **all** collateral in
  the system. Every collateral↔debt conversion, the collateral ratio, mint/redeem share math and
  the rebalance/pre-liquidation triggers derive from this one number.
- **If wrong/compromised:** an over-stated rate lets equity/borrow be over-valued (redeem too
  much / avoid rebalance); an under-stated rate can force rebalances/liquidation. At ~16.7×
  leverage a small mis-report is amplified.
- **On-chain evidence bounding it:** underlying is a **standard Chainlink OCR2** aggregator
  (verified source in `contracts/AccessControlledOCR2Aggregator_…`), not a bespoke pusher; live
  `price()` = 1.10167e36 is consistent with the current weETH exchange rate; feed description
  reads "weETH / eETH Exchange Rate". The transmitter/signer set and their keys are off-chain
  (Chainlink DON) — not readable. The feed **owner** (Safe 4-of-9 `0xf0db7318`) can swap the
  aggregator on-chain; that swap *is* observable but the operators behind it are not.

### U2 — LayerZero bridge for weETH (OFT mint authority)
- **Where:** collateral weETH `0x04c0599a` is an `EtherfiOFTUpgradeable` bound to LayerZero
  `EndpointV2 0x1a440760`.
- **Decision it controls:** whether a "weETH was received from another chain" message is genuine,
  i.e. whether new weETH may be **minted on Base**. The system assumes each Base weETH is backed
  by a real lock/burn on the source chain.
- **If wrong/compromised:** a forged cross-chain message (compromised DVN/executor set, or a
  malicious peer) mints unbacked weETH → collateral supply inflation → the Morpho market and
  every position priced against it are backed by less than they think.
- **On-chain evidence bounding it:** endpoint is the **canonical LayerZero EndpointV2** (same
  address verified on Base and Ethereum mainnet — see `docs/INTEGRITY.md`); OFT is owned by the
  **EtherFiTimelock** `0x851dd540`. The specific DVN/executor/peer configuration and the
  source-chain lock accounting live **off-chain / on other chains** and are not resolvable from
  the Base destination contract alone. *(This is the "does the destination's notion of a deposit
  match the source" question; answerable only from cross-chain evidence, not from this repo's
  Base-only view.)*

### U3 — EtherFi governance over the collateral asset
- **Where:** `EtherFiTimelock 0x851dd540` owns the weETH `ProxyAdmin 0x2f6f3cc4` **and** the OFT.
- **Decision it controls:** the weETH **implementation** (upgrade) and its LayerZero config.
- **If wrong/compromised:** a malicious weETH upgrade could alter balances/transfer logic under
  the leverage positions — collateral behaviour changes out from under Seamless.
- **On-chain evidence bounding it:** authority is behind a **timelock contract** (verified name
  `EtherFiTimelock`, code in `contracts/EtherFiTimelock_…`), not a raw EOA; ProxyAdmin recovered
  and shown to gate all upgrades behind `owner` only (no secret path — see recovery below).
  EtherFi's timelock delay / proposer set is external protocol governance.

### U4 — Seamless SEAM-token DAO (ultimate on-chain authority, socially off-chain)
- **Where:** `SeamGovernorV2` (short `0x8768c789` / long `0x04faa282`) over SEAM votes token
  `0x1c7a4604`, driving the 48h and 5-day timelocks.
- **Decision it controls:** after the timelock delay, **upgrade of the LeverageManager and
  RebalanceAdapter and the leverage-token beacon** — i.e. everything.
- **If wrong/compromised:** whoever assembles voting power ≥ threshold (200k) and quorum (15%),
  or captures the guardian/long-timelock path, can re-code the system after 48h (or 5 days for
  role changes).
- **On-chain evidence bounding it:** full governor + dual-timelock + 2-of-3 guardian topology is
  resolved and verified (see MAP + AUTHORITY docs); delays (48h / 5-day) are read live. The SEAM
  **token holder distribution** (who actually has the votes) is a token-balance/social question,
  not fixed by code.

### U5 — Morpho DAO (market venue governance)
- **Where:** Morpho `owner` = 5-of-9 Safe `0xcba28b38`.
- **Decision it controls:** protocol fee on the market and the enabled-IRM/LLTV registry.
- **Bounding evidence:** Morpho Blue is **immutable** and canonical (same address verified Base +
  mainnet); by construction the owner **cannot** move or seize an existing position, and
  `feeRecipient` is currently `0x0`. Lowest-impact of the five.

### U6 — Rebalance keepers / auction counterparties (permissionless, parameters on-chain)
- Rebalances are permissionless Dutch auctions; the *terms* (price multipliers, reward, CR band)
  are on-chain and owned by the timelock (recorded in AUTHORITY doc). No off-chain signer is
  trusted here — listed only to state that the keeper identity is open and not a hidden authority.

---

## Fully recovered (was unverified, now readable) — not a residual gap

### R1 — weETH ProxyAdmin `0x2f6f3cc4` (only unverified contract in the graph)
Recovered in `artifacts/decompiled/0x2f6f3cc4…/` with all three artifacts:
- **Decompilation** (`decompiled.sol`, heimdall-rs v0.8.5) — Ownable admin: `owner()`,
  `transferOwnership`, `renounceOwnership`, `upgradeAndCall(address,address,bytes)`,
  `UPGRADE_INTERFACE_VERSION`="5.0.0".
- **Constants** (`artifacts/constants/0x2f6f3cc4….json`) — **no** hardcoded addresses, **no**
  embedded keys/secrets; only the standard `OwnershipTransferred` event topic. ⇒ there is no
  secret-gated path, because there is no embedded secret to gate one.
- **Simulation** (`…sim.json`) — from `0x…dEaD`: `transferOwnership`, `renounceOwnership`
  (reverts `OwnableUnauthorizedAccount` `0x118cdaa7`) and `upgradeAndCall` all revert. Sole
  authority is `owner` = EtherFiTimelock.
- **Identity:** OpenZeppelin Contracts **v5.0.0 `ProxyAdmin`** (selector set + version string +
  clean constants + decompiled logic all consistent). Residual: byte-for-byte solc match not
  machine-run (no solc in env), but no divergent logic exists in the recovered code. Canonical
  reference source saved alongside for readability, clearly labelled as reference — **not** a
  substitute for the recovered artifacts.

---

## Explicitly NOT gaps (checked, so an auditor doesn't re-chase them)
- **No second Leverage Token / adapter.** Exactly one `LeverageTokenCreated` event on the hub
  (verified via logs); the graph's single-position shape is complete, not truncated.
- **Proxy implementations all resolved** to running code (EIP-1967 / EIP-1167 / beacon slots
  read directly, not trusted from Etherscan's label).
- **No decompiler blocker.** heimdall-rs installed and used successfully; no black boxes remain.
