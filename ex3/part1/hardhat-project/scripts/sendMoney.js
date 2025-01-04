const hre = require("hardhat");
const ethers = hre.ethers;

async function main() {
  // Get the accounts from Hardhat's local network
  const [sender, recipient] = await ethers.getSigners();
  
  // The address we just deployed
  const contractAddress = "0x5FbDB2315678afecb367f032d93F642f64180aa3";
  
  // Get the contract factory
  const Wallet = await ethers.getContractFactory("Wallet");
  
  // Connect to the contract
  const wallet = await Wallet.attach(contractAddress);
  
  console.log(`Sender Address: ${sender.address}`);
  console.log(`Recipient Address: ${recipient.address}`);
  console.log(`Contract Address: ${contractAddress}`);
  
  // Send all funds to the recipient
  const sendTx = await wallet.connect(sender).sendTo(recipient.address);
  await sendTx.wait();
  
  console.log('Funds sent successfully!');
}

// Recommended pattern to handle errors in async functions
main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
