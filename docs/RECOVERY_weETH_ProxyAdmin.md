# Recovery: weETH ProxyAdmin 0x2f6f3cc4a275c7951fb79199f01ed82421edfb68 (UNVERIFIED on-chain)

Role in graph: TransparentUpgradeableProxy admin of the market **collateral token weETH**
(0x04c0599ae5a44757c0af6f9ec3b93da8976c150a). Whoever owns this ProxyAdmin can replace the
weETH implementation, i.e. hold upgrade authority over the leverage system's collateral asset.
This is an EtherFi infrastructure contract (external to Seamless), but it sits in the target's
upstream authority path, so it is recovered here in full.

## Identity (high confidence): OpenZeppelin Contracts v5.0.0 `ProxyAdmin`
Established by three independent artifacts in this directory + selector analysis:

- `decompiled.sol` / `abi.json` — heimdall-rs v0.8.5 decompilation of the runtime bytecode
- `../constants/2f6f3cc4...json` — embedded-constant extraction
- `../constants/2f6f3cc4...sim.json` — unprivileged-caller simulation

### Function selectors (from runtime dispatcher)
| selector   | function                                   |
|------------|--------------------------------------------|
| 0x715018a6 | renounceOwnership()                        |
| 0x8da5cb5b | owner()                                    |
| 0x9623609d | upgradeAndCall(address,address,bytes)      |
| 0xad3cb1cc | UPGRADE_INTERFACE_VERSION()  -> "5.0.0"     |
| 0xf2fde38b | transferOwnership(address)                 |

### Constants
- No PUSH20 hardcoded addresses. No embedded keys/secrets.
- Only PUSH32 constant: 0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0
  = keccak256("OwnershipTransferred(address,address)") (standard event topic).
- UPGRADE_INTERFACE_VERSION string = "5.0.0".

### Guard analysis / simulation (from 0x0000...dEaD, current chain state)
- transferOwnership(addr)        -> revert (onlyOwner)
- renounceOwnership()            -> revert OwnableUnauthorizedAccount(0xdead) [0x118cdaa7]
- upgradeAndCall(proxy,impl,"")  -> revert (cannot upgrade as unprivileged caller)
=> Sole authority is the `owner` storage slot. No secret-gated path exists (no embedded
   key/address to gate one). This is NOT a signature/secret-guarded contract.

### Live authority
- owner() = 0x851dd540f4d2ec78120de0a0cc87b21ede5df5c6 = **EtherFiTimelock** (verified).
  => weETH upgrades are gated behind EtherFi's own timelock/governance, not a raw EOA.

## Residual question
Byte-for-byte compilation match to canonical OZ v5.0.0 `ProxyAdmin` was not machine-verified
(no solc in env), but decompilation + selector set + clean constants + simulation are mutually
consistent with the standard contract and show no divergent logic. See
`ProxyAdmin_reference_OZ_v5.0.0.sol` for the canonical source this bytecode corresponds to
(reference for readability; identity is proven by the recovered artifacts above, not by this file).
