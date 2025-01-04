const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("Wallet Attack", function () {
  let wallet, walletAttack;
  let owner, attacker, victim1, victim2;

  beforeEach(async function () {
    // Get signers
    [owner, attacker, victim1, victim2] = await ethers.getSigners();

    // Deploy Vulnerable Wallet
    const Wallet = await ethers.getContractFactory("Wallet");
    wallet = await Wallet.deploy();
    await wallet.waitForDeployment();

    // Deploy Attack Contract
    const WalletAttack = await ethers.getContractFactory("WalletAttack");
    walletAttack = await WalletAttack.connect(attacker).deploy();
    await walletAttack.waitForDeployment();

    // Victims deposit funds (4 ETH total)
    await wallet.connect(victim1).deposit({ value: ethers.parseEther("2.0") });
    await wallet.connect(victim2).deposit({ value: ethers.parseEther("2.0") });
  });

  it("Should successfully perform reentrancy attack", async function () {
    // Check initial balances
    const initialWalletBalance = await ethers.provider.getBalance(await wallet.getAddress());
    console.log("Initial Wallet Balance:", ethers.formatEther(initialWalletBalance), "ETH");
    
    const initialAttackerBalance = await ethers.provider.getBalance(attacker.address);
    console.log("Initial Attacker Balance:", ethers.formatEther(initialAttackerBalance), "ETH");

    // Perform the attack with 1 ETH
    await walletAttack.connect(attacker).exploit(await wallet.getAddress(), {
      value: ethers.parseEther("1.0")
    });

    // Check final balances
    const finalWalletBalance = await ethers.provider.getBalance(await wallet.getAddress());
    console.log("Final Wallet Balance:", ethers.formatEther(finalWalletBalance), "ETH");
    
    const finalAttackerBalance = await ethers.provider.getBalance(attacker.address);
    console.log("Final Attacker Balance:", ethers.formatEther(finalAttackerBalance), "ETH");

    // Verify attack was successful
    expect(finalWalletBalance).to.be.lessThan(initialWalletBalance);
    expect(finalWalletBalance).to.equal(0); // Should drain the wallet completely
  });
});
