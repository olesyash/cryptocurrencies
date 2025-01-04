const hre = require("hardhat");

async function main() {
  // Get the first account from Hardhat's local network
  const [deployer] = await hre.ethers.getSigners();
  
  // The address we just deployed
  const contractAddress = "0x5FbDB2315678afecb367f032d93F642f64180aa3";
  
  // Get the contract factory
  const Wallet = await hre.ethers.getContractFactory("Wallet");
  
  // Connect to the contract
  const wallet = await Wallet.attach(contractAddress);
  
  // Check balance using the new getBalance method
  const balance = await wallet.connect(deployer).getBalance();
  
  console.log(`Depositor Address: ${deployer.address}`);
  console.log(`Contract Address: ${contractAddress}`);
  console.log(`Balance: ${hre.ethers.formatEther(balance)} ETH`);
}

// Recommended pattern to handle errors in async functions
main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
