const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("Rock-Paper-Scissors Game", function () {
  let rps, player1, player2;
  const gameId = 1;
  const betAmount = ethers.parseEther("1.0");

  beforeEach(async function () {
    const RPS = await ethers.getContractFactory("RPS");
    rps = await RPS.deploy(5);
    await rps.waitForDeployment();

    [, player1, player2] = await ethers.getSigners();

    // Deposit funds for players
    await player1.sendTransaction({
      to: await rps.getAddress(),
      value: ethers.parseEther("10")
    });
    await player2.sendTransaction({
      to: await rps.getAddress(),
      value: ethers.parseEther("10")
    });
  });

  it("Should play a full game", async function () {
    // Player 1 chooses Rock (1)
    const move1 = 1; // ROCK
    const key1 = ethers.encodeBytes32String("secret1");
    const commitment1 = ethers.solidityPackedKeccak256(
      ["uint8", "bytes32"],
      [move1, key1]
    );

    // Player 2 chooses Scissors (3)
    const move2 = 3; // SCISSORS
    const key2 = ethers.encodeBytes32String("secret2");
    const commitment2 = ethers.solidityPackedKeccak256(
      ["uint8", "bytes32"],
      [move2, key2]
    );

    // Make moves
    await rps.connect(player1).makeMove(gameId, betAmount, commitment1);
    await rps.connect(player2).makeMove(gameId, betAmount, commitment2);

    // Reveal moves
    await rps.connect(player1).revealMove(gameId, move1, key1);
    await rps.connect(player2).revealMove(gameId, move2, key2);

    // Check game state
    const finalState = await rps.getGameState(gameId);
    console.log("Final Game State:", finalState);

    // Verify balances
    const player1Balance = await rps.balanceOf(player1.address);
    const player2Balance = await rps.balanceOf(player2.address);
    
    console.log("Player 1 Balance:", ethers.formatEther(player1Balance));
    console.log("Player 2 Balance:", ethers.formatEther(player2Balance));

    // Player 1 should win (Rock beats Scissors)
    expect(player1Balance.toString()).to.equal(ethers.parseEther("11").toString());
    expect(player2Balance.toString()).to.equal(ethers.parseEther("9").toString());
  });
});
