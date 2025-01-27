// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract Wallet {
    // This wallet is vulnerable to reentrancy attacks.
    // DO NOT CHANGE THIS FILE

    mapping(address => uint) public userBalances;

    function deposit() external payable {
        //deposits eth into the account of the message sender.
        userBalances[msg.sender] += msg.value;
    }

    // New public function to check balance
    function getBalance() external view returns (uint) {
        return userBalances[msg.sender];
    }

    function sendTo(address payable destination) external {
        //sends eth from the account of the message sender to the destination.
        uint amount = userBalances[msg.sender];
        (bool success, ) = destination.call{value: amount}("");
        require(success);
        userBalances[msg.sender] = 0;
    }
}
