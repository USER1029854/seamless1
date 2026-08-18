// SPDX-License-Identifier: MIT
pragma solidity >=0.8.0;

/// @title            Decompiled Contract
/// @author           Jonathan Becker <jonathan@jbecker.dev>
/// @custom:version   heimdall-rs v0.8.5
///
/// @notice           This contract was decompiled using the heimdall-rs decompiler.
///                     It was generated directly by tracing the EVM opcodes from this contract.
///                     As a result, it may not compile or even be valid solidity code.
///                     Despite this, it should be obvious what each function does. Overall
///                     logic should have been preserved throughout decompiling.
///
/// @custom:github    You can find the open-source decompiler here:
///                       https://heimdall.rs

contract DecompiledContract {
    bytes public constant UPGRADE_INTERFACE_VERSION = 0xBytes([53, 46, 48, 46, 48]);
    
    address public owner;
    
    error OwnableInvalidOwner(address);
    event OwnershipTransferred(address, address);
    
    /// @custom:selector    0x9623609d
    /// @custom:signature   Unresolved_9623609d(address arg0) public pure
    /// @param              arg0 ["address", "uint160", "bytes20", "int160"]
    function Unresolved_9623609d(address arg0) public pure {
        require(arg0 == (address(arg0)));
    }
    
    /// @custom:selector    0xf2fde38b
    /// @custom:signature   transferOwnership(address arg0) public
    /// @param              arg0 ["address", "uint160", "bytes20", "int160"]
    function transferOwnership(address arg0) public {
        require(arg0 == (address(arg0)));
        require(msg.sender == (address(owner)), CustomError_118cdaa7());
        var_a = 0x118cdaa700000000000000000000000000000000000000000000000000000000;
        address var_b = msg.sender;
        require(address(arg0), CustomError_1e4fbdf7());
        owner = (address(arg0)) | (uint96(owner));
        emit OwnershipTransferred(address(owner), address(arg0));
        var_a = 0x1e4fbdf700000000000000000000000000000000000000000000000000000000;
        var_b = 0;
    }
    
    /// @custom:selector    0x715018a6
    /// @custom:signature   renounceOwnership() public
    function renounceOwnership() public {
        require(msg.sender == (address(owner)), CustomError_118cdaa7());
        var_a = 0x118cdaa700000000000000000000000000000000000000000000000000000000;
        address var_b = msg.sender;
        owner = 0 | (uint96(owner));
        emit OwnershipTransferred(address(owner), 0);
    }
}