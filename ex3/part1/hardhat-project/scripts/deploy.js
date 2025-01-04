const hre = require("hardhat");

async function main() {
  // Get the contract factory for the Wallet contract
  const Wallet = await hre.ethers.getContractFactory("Wallet");
  
  // Deploy the contract
  const wallet = await Wallet.deploy();
  
  // Wait for the contract to be deployed
  await wallet.waitForDeployment();
  
  console.log("Wallet contract deployed to:", await wallet.getAddress());
}

// Recommended pattern to handle errors in async functions
main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
