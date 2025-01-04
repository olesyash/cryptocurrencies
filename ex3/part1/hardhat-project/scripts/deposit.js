const hre = require("hardhat");
const ethers = hre.ethers;

async function main() {
  // Get the first account from Hardhat's local network
  const [deployer] = await ethers.getSigners();
  
  // The address we just deployed
  const contractAddress = "0x5FbDB2315678afecb367f032d93F642f64180aa3";
  
  // Get the contract factory
  const Wallet = await ethers.getContractFactory("Wallet");
  
  // Connect to the contract
  const wallet = await Wallet.attach(contractAddress);
  
  // Deposit 1 ETH
  const depositAmount = ethers.parseEther("1.0");
  const depositTx = await wallet.connect(deployer).deposit({ value: depositAmount });
  await depositTx.wait();
  
  console.log(`Deposited ${ethers.formatEther(depositAmount)} ETH`);
  console.log(`Depositor Address: ${deployer.address}`);
  console.log(`Contract Address: ${contractAddress}`);
}

// Recommended pattern to handle errors in async functions
main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
