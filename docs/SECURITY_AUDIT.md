# Security Audit — Seamless LeverageManager + MorphoLendingAdapter (Base 8453)

**Scope (Seamless-authored, on-chain, running code):** LeverageManager `0xfe9101…` (behind
proxy `0x38Ba…`), MorphoLendingAdapter `0x585c…` (clone `0x9558…`), RebalanceAdapter
`0xd923b2…` (DutchAuction + CollateralRatios + PreLiquidation mixins, behind proxy `0xa530e6…`),
LeverageToken `0x603da7…` (BeaconProxy `0xa2fcee…`), BeaconProxyFactory/Beacon `0xe0b2e4…`.

**Adversary model:** unprivileged, well-resourced, flash-loans, many addresses, atomic
multi-step and multi-tx, hostile-but-standards-compliant tokens, extreme inputs. Excluded:
ordering/front-running/sandwich, other-user-dependent, and privileged parties misusing their
own legitimate powers (governance/timelock, oracle operator, EtherFi/LayerZero) — those are
recorded as **trust boundaries** in `docs/UNRESOLVED.md`, not findings.

---

## VERDICT

**No economic or unauthorized-access vulnerability was found in the in-scope Seamless-authored
code, as deployed and configured.** Every value-removing adapter function is `onlyLeverageManager`;
the only permissionless adapter functions (`addCollateral`, `repay`) can *only add* value
(donations). Mint/redeem rounding is uniformly protocol-favorable. Both rebalance paths are
bounded by collateral-ratio-toward-target and equity-loss invariants to the *designed* keeper
reward (≤0.1% via auction multiplier floor; ≤~0.5% of debt-delta via pre-liquidation reward) and
are only reachable in the states they were designed for. There is **no signature/secret-gated
fund path, no hardcoded signer, no delegatecall/arbitrary-call surface** in the deployed
bytecode. The live configuration is internally coherent.

The system's residual risk lives entirely in trust boundaries that are **out of scope by the
model above** and are documented separately: the Chainlink weETH/eETH exchange-rate oracle,
the 48h-timelock/DAO upgrade authority over every implementation, and the upgradeable +
LayerZero-bridge-minted weETH collateral. See "Trust-boundary caveats" at the end.

---

## ARTIFACT 1 — Complete external entry-point enumeration

Mechanically extracted from source (`tools/entrypoints.py`); every state-changing external/public
function, fallback, and receive is listed with its guard and the one-line reason it is not
abusable. View/pure getters are omitted from the abuse analysis (no state written) but were
checked for use as manipulable inputs in Artifact 2.

### LeverageManager (proxy `0x38Ba…`, UUPS + AccessControl)
| Function | Guard | Why an arbitrary caller can't abuse it |
|---|---|---|
| `initialize` | `initializer` | Already initialized (live admin/treasury/factory set); locked. |
| `createNewLeverageToken` | `nonReentrant`, permissionless *by design* | Creates an isolated token with caller-chosen adapters; cannot touch existing tokens (per-token immutable config, no shared balances). Reusing the **live** adapters reverts (`authorizedCreator`/`isUsed`/`leverageToken` already bound). Attacker-created tokens only endanger users who opt into them (documented user risk). |
| `deposit` / `mint` | `nonReentrant` + `minShares`/`maxCollateral` slippage | Pulls collateral, borrows debt, mints shares in constant proportion (CR preserved). Shares floor-rounded, debt-out floor-rounded → protocol-favorable. Caller pays full value. |
| `redeem` / `withdraw` | `nonReentrant` + `minCollateral`/`maxShares` slippage | Burns shares, repays debt (Ceil), returns collateral (Floor) → protocol-favorable rounding. Caller receives ≤ pro-rata. |
| `rebalance` | `nonReentrant` + `isEligibleForRebalance` + `isStateAfterRebalanceValid` | Direct (non-adapter) caller only eligible when CR < pre-liq threshold; result must move CR strictly toward target and cap equity loss at `debtDelta × rebalanceReward% ` (~0.5%). Conservation ⇒ attacker gain ≤ that bound. (Detail in Artifact 2 §R.) |
| `chargeManagementFee` | public (permissionless) | Only mints the *accrued* management fee to treasury; management fee = 0 live ⇒ inert. Early-returns on 0; cannot be spammed to over-mint. |
| `setDefaultManagementFeeAtCreation` / `setManagementFee` / `setTreasury` / `setTreasuryActionFee` | `onlyRole(FEE_MANAGER_ROLE)` | Role currently unheld ⇒ callable by nobody. Governance-only. |
| `upgradeToAndCall` (UUPS) | `onlyRole(UPGRADER_ROLE)` | Timelock-only (trust boundary). |
| view getters / `convert*` / `preview*` | — | No state written; used as inputs → analyzed in Artifact 2. |

### MorphoLendingAdapter (impl `0x585c…`, clone `0x9558…`)
| Function | Guard | Why safe |
|---|---|---|
| `initialize` | `initializer` | Clone already initialized (`isUsed=true`); locked. |
| `postLeverageTokenCreation` | `onlyLeverageManager` + `creator==authorizedCreator` + `!isUsed` | One-shot binding; already used. |
| `addCollateral` | **none (permissionless)** | Pulls collateral **from `msg.sender`** and supplies it to the position. Strictly *increases* collateral/CR/equity — a donation. Cannot remove value; economically self-harming to abuse. |
| `repay` | **none (permissionless)** | Pulls debt asset **from `msg.sender`** and repays the position. Strictly *reduces* debt / raises CR — a donation. "Repay-all" path caps at owed shares; no over-withdrawal. |
| `removeCollateral` / `borrow` | `onlyLeverageManager` | The only value-*removing* ops; gated to the manager, which enforces slippage/rebalance invariants. |
| view getters | — | Priced off Morpho + oracle; analyzed in Artifact 2. |

### RebalanceAdapter (impl `0xd923b2…`, proxy `0xa530e6…`, UUPS + Ownable)
| Function | Guard | Why safe |
|---|---|---|
| `initialize` | `initializer` | Locked (live owner/params set). |
| `postLeverageTokenCreation` | `msg.sender==leverageManager` + `creator==authorizedCreator` + `_setLeverageToken` (one-shot) | Bound to one token already. |
| `createAuction` | permissionless | Only succeeds if no *valid* auction ongoing (`endAuction()` reverts while valid) **and** token is eligible (CR outside band). Direction derived from live state, not caller. ⇒ cannot reset/grief a running auction, cannot force a wrong-direction auction. |
| `endAuction` | permissionless | Reverts while the auction is still valid; only clears an invalid one. |
| `take` | permissionless + `isAuctionValid()` | Trades collateral↔debt at `oracle × multiplier`, multiplier ∈ [0.999, 1.01] ⇒ ≤0.1% to taker; routes through `LeverageManager.rebalance` whose invariants forbid overshooting past target. Bounded, designed keeper reward. (Artifact 2 §A.) |
| `upgradeToAndCall` (UUPS) | `onlyOwner` | Timelock-only (trust boundary). |

### LeverageToken (impl `0x603da7…`, BeaconProxy `0xa2fcee…`, ERC20 + ERC20Permit)
| Function | Guard | Why safe |
|---|---|---|
| `initialize` | `initializer` | Locked. |
| `mint` / `burn` | `onlyOwner` (= LeverageManager) | Supply only moves via manager mint/redeem accounting. |
| `permit` / ERC20 transfers | EIP-2612 (OZ) | Standard; domain bound to this token's name+chainid+address ⇒ no cross-contract/cross-chain replay. |

### BeaconProxyFactory / UpgradeableBeacon (`0xe0b2e4…`)
| Function | Guard | Why safe |
|---|---|---|
| `createProxy` | permissionless | `Create2` salt = `keccak256(sender, baseSalt)`; different `sender` ⇒ disjoint address space ⇒ no squatting on the LeverageManager's deterministic token addresses; only deploys the fixed BeaconProxy creation code (no arbitrary bytecode). |
| `upgradeTo` (beacon) | `onlyOwner` | Timelock-only (re-codes all leverage tokens; trust boundary). |
| `computeProxyAddress` / `numProxies` | view | No state. |

**No `fallback`/`receive` exists in any in-scope contract** (proxies use OZ `Proxy._fallback`
delegating to the fixed implementation slot — checked byte-identical to OZ v5.1.0).

---

## ARTIFACT 2 — State-dependency map & compositions examined

**Writer → reader state dependencies (the whole system):**

| State | Written by | Read by (and trusted for) |
|---|---|---|
| Morpho collateral of adapter | `addCollateral`(perm), `removeCollateral`(LM), Morpho liquidation | `getCollateral*` → mint/redeem share & debt pricing; CR; auction pricing |
| Morpho debt of adapter (`expectedBorrowAssets`) | `borrow`(LM), `repay`(perm), interest accrual, liquidation | `getDebt` → mint/redeem pricing; CR; equity; pre-liq equity bound |
| LeverageToken `totalSupply` | `mint`/`burn`(LM-owner), fee mints | share↔collateral/debt conversions |
| Oracle `price()` | Chainlink OCR2 (off-chain) | every collateral↔debt conversion, CR, auction price |
| `auction` struct | `createAuction`/`take`/`endAuction`(perm) | `isAuctionValid`, `getAmountIn` |
| CR-band / multipliers / reward (immutable post-init) | init only | eligibility + validity guards |
| Roles / owner / beacon impl | governance | upgrade & param authority (trust boundary) |

**Compositions worked (single actor, atomic and multi-tx, flash-loan-funded):**

- **§R Direct `rebalance` (pre-liq path).** Attacker supplies arbitrary `actions` + `amountIn/amountOut`.
  Eligible only if CR < 1.0606 (needs a *real* oracle drop; not attacker-inducible atomically —
  exchange-rate oracle, not spot AMM). Guards force CR strictly up toward target **and**
  `equityAfter ≥ equityBefore − debtDelta×(liqPenalty×reward%/1e4)` ≈ `debtDelta×0.503%`. By
  conservation the attacker's gain equals the position's equity loss ⇒ gain ≤ 0.503% of debt
  repaid, i.e. the designed pre-liquidation reward (and < Morpho's 1.68% liq penalty). Attempts
  to borrow-and-run, remove-and-run, or no-op-extract all fail the CR-must-increase / balance
  checks. **Not profitable, not unauthorized.**
- **§A Auction `take`.** Reachable only via the adapter (caller==self), priced at
  `oracle×multiplier`, multiplier floor 0.999 ⇒ ≤0.1% of notional to the taker; `isStateAfterRebalanceValid`
  forbids overshooting past target, so notional is bounded by the (tight) CR-band drift. Repeated
  takes within one auction stop when CR re-enters the band. New auctions require the market to
  push CR back out. **Bounded designed incentive.**
- **Donation griefing (`addCollateral`/`repay`) → share price / mint terms.** Donations raise
  collateral/equity for *all* holders pro-rata; attacker recovers only their share ⇒ net loss.
  Cannot round a normal deposit's shares to 0 without donating economically-impossible amounts
  (>1e18 weETH). Cannot be interleaved into a `rebalance` (nonReentrant; weETH/WETH have no
  transfer hooks). **No profit.**
- **Mint/redeem repetition (N small vs 1 large).** Redeem collateral-out is `Floor`, debt-in is
  `Ceil`; mint shares-out and debt-out are `Floor`. Every split loses ≤1 wei to the splitter each
  time (rounding is uniformly against the caller). Splitting is strictly worse. **No gain.**
- **Auction dust rounding.** `take(amountOut≈1 wei)` can floor `amountIn` to 0, but the
  `ratioAfter != ratioBefore` check rejects sub-threshold moves, and 1 wei ≪ gas. **No economic
  gain, path is authorized-by-design.** (Recorded, dismissed.)
- **First-deposit / inflation.** Live token is seeded (supply 1.17e18, 20 weETH). The empty-vault
  path only exists for *new* tokens an attacker creates for themselves. **Out of victim scope.**
- **Create2 / factory squatting, adapter re-binding, re-initialization.** All blocked
  (sender-scoped salt; one-shot `isUsed`/`_setLeverageToken`; `initializer`-locked). **Closed.**
- **Reentrancy.** Manager entrypoints `nonReentrant`; collateral=weETH (OFT, standard ERC20 `_update`,
  no hook) and debt=WETH9 (no hook) ⇒ no callback to re-enter `take`/`rebalance` mid-flow.

---

## Trust-boundary caveats (out of scope by the adversary model; NOT proven safe here)

A clean on-chain result does **not** imply the system is sound end-to-end. Safety additionally
depends on:

1. **Oracle** — the weETH/eETH Chainlink OCR2 exchange-rate feed drives *all* pricing. It is not
   atomically manipulable (exchange rate, not a spot pool), but a stale/compromised feed, or the
   4-of-9 feed-owner Safe swapping the aggregator, mis-prices the entire system. Off-chain;
   evidenced but unverifiable from the destination code.
2. **Governance upgrade** — `UPGRADER_ROLE`/`owner`/beacon-owner all = the 48h SeamTimelock
   (DAO-driven). It can replace *any* implementation and thereby move all funds. A trusted-party
   power (excluded), but it is the single largest authority in the graph.
3. **Collateral (weETH)** — upgradeable by EtherFi's ProxyAdmin and mint-authorized by the
   LayerZero bridge. A malicious weETH upgrade or a forged cross-chain mint would undermine the
   collateral the leverage token is priced against. External-protocol trust.

See `docs/UNRESOLVED.md` for each with the decision it controls and the on-chain evidence bounding it.
