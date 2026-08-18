# Trust Graph Map — Seamless LeverageManager + MorphoLendingAdapter (Base 8453)

The two targets were resolved in **both directions**: everything they lean on (downstream),
and everything that holds power over them (upstream). Proxies are resolved to the
implementation that actually runs. The graph converges at **35 nodes**; every node with code
is verified except one (the weETH ProxyAdmin, recovered in `artifacts/decompiled/`).

Addresses are clickable in `docs/INVENTORY.md`; live values are in
`docs/AUTHORITY_AND_STATE.md`.

```
                          SEAM token holders (0x1c7a4604, ERC20Votes)
                                    │  vote
                     ┌──────────────┴───────────────┐
             SeamGovernorV2 (short)          SeamGovernorV2 (long)
             0x8768c789  →impl 0xc3a36d72     0x04faa282 →impl 0xc3a36d72
                     │ propose/execute               │ propose/execute
                     ▼                                ▼
        SeamTimelockController (48h)  ◄──admin── SeamTimelockController (5-day)
        0x639d2dd2  →impl 0x13f5b4               0xa9644846 →impl 0xbe170d7d
        (also TREASURY)                          (self-administered)
                     │                                 ▲
   Guardian Safe 2/3 │ CANCELLER ────────────────────┘ CANCELLER
   0xa1b5f2cc         │
                      │ DEFAULT_ADMIN_ROLE + UPGRADER_ROLE (48h delay)
                      │ owner() of RebalanceAdapter + BeaconFactory/Beacon
   ┌──────────────────┼───────────────────────────────────────────────┐
   │ UPGRADE / PARAM AUTHORITY over the entire leverage system         │
   ▼                  ▼                          ▼
TARGET 1                          RebalanceAdapter proxy        BeaconProxyFactory
LeverageManager proxy 0x38Ba      0xa530e6ea →impl 0xd923b252   +UpgradeableBeacon 0xe0b2e40e
  →impl 0xfe9101 (LeverageManager) (DutchAuction+PreLiq+          owner=timelock
  UUPS; AccessControl                CollateralRatios; UUPS)      implementation()=
  roles→timelock                   owner=timelock                0x603da735 (LeverageToken)
   │ manages                        │ prices rebalances           │ beacon for
   ▼                                ▼                              ▼
LeverageToken shares (BeaconProxy) 0xa2fceeae ──beacon──► 0xe0b2e40e ──impl──► 0x603da735
"weETH / WETH 17x Leverage Token"
   │ position custody delegated to
   ▼
TARGET 2                                   authorizedCreator = 0x0b26272f (deployer EOA, one-shot, spent)
MorphoLendingAdapter clone 0x9558  ──impl(EIP1167)──►  0x585cc1c8 (MorphoLendingAdapter)
   │ immutable: leverageManager=0x38Ba, morpho=0xbbbb…ffcb
   │ opens/holds ONE position on Morpho market fd0895…cfea
   ▼
Morpho Blue 0xbbbb…ffcb  (owner: Morpho DAO Safe 5/9 0xcba28b38; feeRecipient=0; canonical)
   ├── IRM   AdaptiveCurveIrm 0x46415998            (canonical Morpho IRM)
   ├── LLTV  0.945
   ├── loan  WETH9 0x4200…0006                      (canonical Base predeploy)
   ├── collat weETH 0x04c0599a (TransparentProxy)   →impl 0xde8a2c33 (EtherfiOFTUpgradeable)
   │          ├ ProxyAdmin 0x2f6f3cc4 (UNVERIFIED→recovered) owner=EtherFiTimelock 0x851dd540
   │          ├ OFT owner  EtherFiTimelock 0x851dd540
   │          └ LZ endpoint 0x1a440760 (EndpointV2) ── cross-chain mint authority (off-chain)
   └── oracle MorphoChainlinkOracleV2 0xce629400
              └ BASE_FEED_1 = EACAggregatorProxy 0x35e9d700  "weETH / eETH Exchange Rate"
                    ├ underlying = Chainlink AccessControlledOCR2Aggregator 0x764a8f2f (off-chain DON)
                    └ feed owner = Safe 4/9 0xf0db7318 (can swap the aggregator)
```

## Downstream — what the targets lean on

**Target 1 (LeverageManager)** holds no user funds itself; it is the orchestrator.
Behaviourally it reaches:
- **FeeManager** (inherited into the same proxy) → `treasury` = `0x639d2dd2` (the timelock);
  all fees currently 0.
- **BeaconProxyFactory / UpgradeableBeacon** `0xe0b2e40e` → the `LeverageToken` implementation
  `0x603da735` that every share-token beacon-proxy runs. Changing the beacon impl re-codes
  **all** leverage tokens at once. Owner = timelock.
- Per-Leverage-Token config (immutable once created): the **LendingAdapter** (Target 2) and
  the **RebalanceAdapter** `0xa530e6ea`.
- The **LeverageToken** share contract `0xa2fceeae` (BeaconProxy) it mints/burns.

**Target 2 (MorphoLendingAdapter clone `0x9558`)** is where the money actually sits. Its
immutables (baked into impl `0x585c`, shared by all clones) are `leverageManager=0x38Ba` and
`morpho=0xbbbb…ffcb`; its per-clone storage pins one Morpho market. It reaches:
- **Morpho Blue** `0xbbbb…ffcb` — custody host; the adapter's collateral (20.13 weETH) and
  debt (20.85 WETH) live *inside* Morpho, not idle in the adapter (verified: adapter token
  balances are 0 weETH / 1 wei WETH).
- **Market oracle** `0xce629400` (MorphoChainlinkOracleV2) → the **weETH/eETH exchange-rate**
  Chainlink feed. This single price drives every collateral↔debt conversion, and therefore
  the collateral ratio, mint/redeem math, and rebalance/liquidation triggers. **This is the
  most security-relevant downstream dependency.**
- **IRM** `0x46415998`, **collateral** weETH `0x04c0599a`, **loan** WETH `0x4200…0006`.

**RebalanceAdapter `0xa530e6ea`** (reached via the Leverage Token's config) runs the Dutch
auctions that set the price at which rebalancers buy/sell the position's collateral/debt to
restore the target collateral ratio. Its owner (the timelock) sets `minPriceMultiplier`
(0.999), `initialPriceMultiplier` (1.01), `rebalanceReward` (30% of `REWARD_BASE` 10000), the
CR band and the pre-liquidation threshold — i.e. the terms on which value leaves the position
during a rebalance. See `docs/AUTHORITY_AND_STATE.md`.

## Upstream — what holds power over the targets (without being them)

- **`SeamTimelockController` (48h) `0x639d2dd2`** holds, on the LeverageManager,
  `DEFAULT_ADMIN_ROLE` **and** `UPGRADER_ROLE`. `UPGRADER_ROLE` authorises the UUPS upgrade of
  the LeverageManager implementation → **total control of the hub after a 48h delay**. The same
  address is `owner()` of the RebalanceAdapter (its UUPS upgrade + all rebalance params) and of
  the BeaconProxyFactory/Beacon (the leverage-token impl). It is also the fee `treasury`.
  One address is the single on-chain choke point for the whole system; it is a timelock, not an
  EOA.
- **Who drives that timelock:** `PROPOSER`/`EXECUTOR` = **`SeamGovernorV2` (short)** `0x8768c789`
  (OZ Governor over the SEAM votes token, 48h voting delay / 72h period / 200k proposal
  threshold / 15% quorum). `CANCELLER` = the governor **and** a **2-of-3 Guardian Safe**
  `0xa1b5f2cc`. The timelock's own `DEFAULT_ADMIN` is a **second, 5-day `SeamTimelockController`**
  `0xa9644846`, driven by a **long** `SeamGovernorV2` `0x04faa282`; that long timelock can
  grant/revoke roles on the 48h timelock.
- **`authorizedCreator` = `0x0b26272f`** (deployer **EOA**) was permitted to create the one
  Leverage Token / use the adapter; `isUsed=true`, so this one-shot power is spent. Recorded
  because an EOA held a creation-time authority.
- **Over the collateral (weETH):** `EtherFiTimelock 0x851dd540` owns both the weETH **OFT**
  (LayerZero config) and the weETH **ProxyAdmin** `0x2f6f3cc4` (can upgrade the weETH
  implementation). The **LayerZero bridge** can mint weETH on Base. **Over the price:** the
  Chainlink **OCR2 DON** reports the rate, and a **4-of-9 Safe `0xf0db7318`** owns the feed
  proxy and can swap the underlying aggregator. These are upstream of the target's value even
  though the Seamless code never names them — see `docs/UNRESOLVED.md`.
- **Over the market venue:** the **Morpho DAO** (5-of-9 Safe `0xcba28b38`) can set the Morpho
  protocol fee and enable/disable IRMs & LLTVs, but **cannot** move or seize an existing
  position.

## Why the graph stops where it stops

This LeverageManager has exactly **one** `LeverageTokenCreated` event (verified via logs), so
there is one LendingAdapter (Target 2), one RebalanceAdapter, one share token, one market.
Outward branches terminate at (a) canonical, cross-chain-identical infrastructure (Morpho,
WETH, LayerZero EndpointV2, Safe singletons — see `docs/INTEGRITY.md`), (b) external-protocol
governance (EtherFi, Morpho, Chainlink) named and evidenced but not owned by Seamless, and
(c) EOAs / Safe owner sets. None of these grows new *Seamless* code, so the graph is complete,
not truncated.
