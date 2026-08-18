// SPDX-License-Identifier: MIT
// REFERENCE ONLY — canonical OpenZeppelin Contracts v5.0.0 ProxyAdmin.
// The deployed runtime at 0x2f6f3cc4a275c7951fb79199f01ed82421edfb68 is UNVERIFIED on-chain.
// Its identity as this contract is established by the recovered artifacts in this directory
// (heimdall decompilation, constant extraction, unprivileged simulation) + selector match,
// NOT by fetching verified source from this deployment. Provided for auditor readability.
pragma solidity ^0.8.20;

import {ITransparentUpgradeableProxy} from
    "@openzeppelin/contracts/proxy/transparent/TransparentUpgradeableProxy.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

contract ProxyAdmin is Ownable {
    string public constant UPGRADE_INTERFACE_VERSION = "5.0.0";

    constructor(address initialOwner) Ownable(initialOwner) {}

    function upgradeAndCall(ITransparentUpgradeableProxy proxy, address implementation, bytes memory data)
        public
        payable
        virtual
        onlyOwner
    {
        proxy.upgradeToAndCall{value: msg.value}(implementation, data);
    }
    // + Ownable: owner(), transferOwnership(address), renounceOwnership()
    //   guarded by onlyOwner -> reverts OwnableUnauthorizedAccount(caller) [0x118cdaa7]
}
