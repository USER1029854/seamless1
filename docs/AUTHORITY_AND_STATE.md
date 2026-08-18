# Live Authority & Configuration State

Snapshot at Base block **~50,121,148** (2026-08-18). Machine-readable copy:
`state/live_state.json`. All values read live via `eth_call` / `eth_getStorageAt` / event logs.

## 1. Authority state (who holds power *right now*)

### LeverageManager `0x38Ba…` (AccessControl + UUPS)
| Role | Holder | Meaning |
|------|--------|---------|
| `DEFAULT_ADMIN_ROLE` | `0x639d2dd2` (SeamTimelock 48h) | grant/revoke every role |
| `UPGRADER_ROLE` | `0x639d2dd2` (SeamTimelock 48h) | **UUPS upgrade of the implementation → total control** |
| `FEE_MANAGER_ROLE` | **none granted** | until admin grants it, fees/treasury cannot be changed |

Reconstructed from `RoleGranted`/`RoleRevoked` logs and re-verified with live `hasRole`.
EIP-1967 impl slot confirms implementation `0xfe9101…`; admin slot empty (UUPS, no separate
proxy admin).

### RebalanceAdapter `0xa530e6ea` (Ownable + UUPS)
`owner()` = `0x639d2dd2` (timelock) → UUPS upgrade **and** every rebalance parameter below.

### BeaconProxyFactory / UpgradeableBeacon `0xe0b2e40e`
`owner()` = `0x639d2dd2` (timelock); `implementation()` = `0x603da735`. Owner can re-point the
beacon → recodes **all** leverage tokens simultaneously.

### SeamTimelockController #1 (48h) `0x639d2dd2`  — the system choke point
- `getMinDelay()` = **172800 s (48h)**
- `PROPOSER_ROLE`, `EXECUTOR_ROLE` = `0x8768c789` (SeamGovernorV2 short)
- `CANCELLER_ROLE` = `0x8768c789` **and** `0xa1b5f2cc` (Guardian Safe 2-of-3)
- `DEFAULT_ADMIN_ROLE` = `0xa96448469520…` (SeamTimelockController #2, 5-day)

### SeamTimelockController #2 (long, 5-day) `0xa9644846`
- `getMinDelay()` = **432000 s (5 days)**
- `PROPOSER`/`EXECUTOR` = `0x04faa282` (SeamGovernorV2 long); `CANCELLER` = `0xa1b5f2cc`,
  `0x04faa282`; `DEFAULT_ADMIN` = itself (self-administered). This timelock is the admin of #1.

### SeamGovernorV2 (short) `0x8768c789`
`token` = `0x1c7a4604` (SEAM votes); `votingDelay` 48h; `votingPeriod` 72h;
`proposalThreshold` 200,000e18; `quorumNumerator` 15%; `timelock` = `0x639d2dd2`.

### Guardian Gnosis Safe `0xa1b5f2cc` — 2-of-3
Owners: `0x53352a00…`, `0x41240c8e…`, `0x490cfd8a…`.

### Collateral (weETH) authority
- ProxyAdmin `0x2f6f3cc4` (OZ v5 ProxyAdmin, recovered) `owner()` = `0x851dd540`
  (**EtherFiTimelock**) → can upgrade the weETH implementation.
- weETH OFT `owner()` = `0x851dd540` (EtherFiTimelock) → LayerZero peer/DVN config.

### Price-feed authority
- EACAggregatorProxy `0x35e9d700` `owner()` = Safe **4-of-9** `0xf0db7318` → can swap the
  underlying aggregator (change the price source).
- Underlying `0x764a8f2f` = Chainlink `AccessControlledOCR2Aggregator` (off-chain DON).

### Market venue authority
- Morpho `owner()` = `0xcba28b38` (Morpho DAO Safe **5-of-9**); `feeRecipient` = `0x0`
  (no protocol fee). Morpho owner cannot touch existing positions.

## 2. Configuration state (parameters the code's correctness depends on)

### The one Leverage Token — `weETH / WETH 17x Leverage Token` (`0xa2fceeae`)
| Param | Value | Notes |
|-------|-------|-------|
| symbol / decimals | `WEETH-WETH-17x` / 18 | ERC20 shares |
| mint fee / redeem fee | 0 / **10** | scale = 1e4 → redeem = **0.10%** (`MAX_FEE` doc: 1e4-1) |
| treasury fees (mint/redeem/mgmt) | 0 / 0 / 0 | `FEE_MANAGER_ROLE` unheld |

### Rebalance parameters (RebalanceAdapter `0xa530e6ea`)
| Param | Value (1e18 / bps) | Meaning |
|-------|--------------------|---------|
| minCollateralRatio | 1.06135 | below → rebalance allowed (raise CR) |
| targetCollateralRatio | 1.0625 | auction targets this |
| maxCollateralRatio | 1.062893082 | above → rebalance allowed (lower CR) |
| preLiquidationCollateralRatioThreshold | 1.0606100 | fast-track pre-liquidation trigger |
| auctionDuration | 3600 s | Dutch auction length |
| initialPriceMultiplier | 1.01 | auction start price |
| minPriceMultiplier | 0.999 | auction floor price |
| rebalanceReward | 3000 / 10000 = **30%** | rebalancer reward share |
| `BASE_RATIO` | 1e18 = 1:1 | ⇒ target CR 1.0625 ≈ **16.7× leverage** |

### Morpho market `0xfd0895ba…cfea`
loanToken WETH `0x4200…0006` · collateralToken weETH `0x04c0599a` · oracle `0xce629400` ·
irm `0x46415998` · **lltv 0.945**. The adapter's stored `marketParams` matches Morpho's live
`idToMarketParams` exactly (consistent).

### Oracle `0xce629400` (MorphoChainlinkOracleV2)
`BASE_FEED_1` = `0x35e9d700` ("weETH / eETH Exchange Rate", 18 dp); `BASE_FEED_2`,
`QUOTE_FEED_1/2`, `BASE_VAULT`, `QUOTE_VAULT` all zero (single-feed); `SCALE_FACTOR` 1e18;
live `price()` = 1.101667e36 ⇒ 1 weETH = **1.10167 WETH**.

### Live position (consistency check — all values reconcile)
| Metric | Value |
|--------|-------|
| LeverageToken totalSupply | 1.17045 shares |
| collateralInDebtAsset | 22.1763 WETH |
| debt | 20.8470 WETH |
| equity | 1.3293 WETH |
| collateralRatio | **1.06376** (inside band, just above target) |
| adapter collateral in Morpho | 20.1297 weETH |
| adapter idle balances | 0 weETH, 1 wei WETH (custody is inside Morpho) |

## 3. Flagged observations (facts, not exploitability judgements)

1. **Single-address authority convergence.** `DEFAULT_ADMIN_ROLE` + `UPGRADER_ROLE` on the
   hub, `owner` of the RebalanceAdapter, `owner` of the beacon, and the fee `treasury` are the
   **same** `0x639d2dd2`. It is a 48h timelock behind a token DAO + guardian, not an EOA — but
   a compromise/capture of the governance path is a single point that reaches the entire system
   after the delay.
2. **Price = intrinsic exchange rate, not market price.** The oracle prices weETH via the
   **weETH/eETH exchange-rate** feed (and treats eETH≈ETH), not a weETH/WETH market price. This
   is immune to weETH secondary-market depeg but fully trusts (a) the eETH:ETH parity
   assumption and (b) the Chainlink OCR2 rate + the 4-of-9 Safe that can swap the aggregator.
3. **Very high leverage, tight band.** Target CR 1.0625 (~16.7×) with the whole rebalance band
   (1.06135–1.062893) and pre-liquidation trigger (1.06061) sitting just above the market's
   liquidation point (LLTV 0.945 ⇒ liquidation CR ≈ 1.0582). Correct code on these parameters
   still runs with a very small buffer.
4. **Collateral is upgradeable + bridge-minted.** weETH is a TransparentUpgradeableProxy
   (EtherFi can swap its implementation via ProxyAdmin `0x2f6f3cc4`) and a LayerZero OFT (minted
   on cross-chain receive). Both are external trust the Seamless code inherits silently.
5. **`FEE_MANAGER_ROLE` unheld** — fees are frozen at their current (0 / 0.10%) values until the
   admin grants the role.
