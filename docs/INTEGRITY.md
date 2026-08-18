# Integrity Checks — shared building blocks vs known-good upstream

Verifies that the "standard" pieces the target is built from are actually standard, checked
against **real upstream** (GitHub release tags / cross-chain canonical deployments), not against
a copy that shipped with the project. A doctored baseline would make diff-based review blind, so
this is checked explicitly. Raw results: `state/integrity_oz_leveragemanager.json`,
`state/integrity_oz_proxies.json`.

## OpenZeppelin source — byte-identical to OZ v5.1.0  ✅
For each embedded OZ file, its SHA-256 was matched against the same path across OZ release tags
(v5.0.0 / v5.0.1 / v5.0.2 / **v5.1.0** / v5.2.0 / v5.3.0). Every security-critical file matched
**v5.1.0 exactly** (whitespace-normalised). No modifications.

Checked in **LeverageManager** (`openzeppelin-contracts[-upgradeable]`):
`AccessControlUpgradeable`, `UUPSUpgradeable`, `Initializable`, `ERC20Upgradeable`,
`ReentrancyGuardTransientUpgradeable`, `ERC1967Utils`, `ECDSA`, `SafeERC20` — all **IDENTICAL**.

Checked in the **deployed proxies + adapters**:
- Target-1 proxy shell `ERC1967Proxy`: `Proxy.sol`, `ERC1967Proxy.sol`, `ERC1967Utils.sol` — IDENTICAL
- LeverageToken `BeaconProxy`: `Proxy`, `ERC1967Utils`, `BeaconProxy` — IDENTICAL
- `BeaconProxyFactory`: `Ownable`, `Proxy`, `ERC1967Utils`, `BeaconProxy`, `UpgradeableBeacon` — IDENTICAL
- `RebalanceAdapter`: `ERC1967Utils`, `OwnableUpgradeable`, `Initializable`, `UUPSUpgradeable` — IDENTICAL
- `MorphoLendingAdapter`: `Initializable` — IDENTICAL

⇒ The proxy/upgrade/access primitives the whole trust model rests on are stock OZ v5.1.0.

## Canonical external infrastructure — same address verified on Base **and** Ethereum mainnet  ✅
Cross-chain identity check (Etherscan V2 chainid 8453 vs 1):

| Contract | Address | Base | Mainnet | Verdict |
|----------|---------|------|---------|---------|
| Morpho Blue | `0xbbbb…ffcb` | Morpho ✓ | Morpho ✓ | canonical multi-chain deployment |
| LayerZero EndpointV2 | `0x1a440760` | EndpointV2 ✓ | EndpointV2 ✓ | canonical |
| Gnosis Safe L2 singleton | `0xfb1bffc9` | GnosisSafeL2 ✓ | GnosisSafeL2 ✓ | canonical Safe singleton |
| Morpho AdaptiveCurveIrm | `0x46415998` | AdaptiveCurveIrm ✓ | (Base-only addr) | standard Morpho IRM, verified on Base |
| WETH9 | `0x4200…0006` | WETH9 ✓ | n/a (Base predeploy) | canonical OP-stack predeploy |

## Recovered contract identity
- weETH ProxyAdmin `0x2f6f3cc4` (unverified on-chain) → OZ v5.0.0 `ProxyAdmin` by decompilation +
  selectors + clean constants (`docs/UNRESOLVED.md` R1). No divergent logic.

## Notes / limits
- The weETH token proxy shell (`TransparentUpgradeableProxy 0x04c0599a`) and its
  `EtherfiOFTUpgradeable` implementation are EtherFi contracts (verified source saved); their OZ
  files were not diffed here because they are external-protocol code, not part of the Seamless
  baseline under review — flagged rather than silently trusted.
- OZ diff is source-level (whitespace-normalised SHA-256). Bytecode-level equivalence of the
  Seamless-authored contracts is implied by Etherscan verification of the deployed runtime.
