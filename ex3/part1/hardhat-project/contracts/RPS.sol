// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

enum GameState {
    NO_GAME, //signifies that there is no game with this id (or there was and it is over)
    MOVE1, //signifies that a single move was entered
    MOVE2, //a second move was enetered
    REVEAL1, //one of the moves was revealed, and the reveal phase just started
    LATE // one of the moves was revealed, and enough blocks have been mined since so that the other player is considered late.
} // These correspond to values 0,1,2,3,4

enum Move {
    NONE,
    ROCK,
    PAPER,
    SCISSORS
} //These correspond to values 0,1,2,3

interface IRPS {
    // WARNING: Do not change this interface!!! these API functions are used to test your code.
    function getGameState(uint gameID) external view returns (GameState);
    function makeMove(uint gameID, uint betAmount, bytes32 hiddenMove) external;
    function cancelGame(uint gameID) external;
    function revealMove(uint gameID, Move move, bytes32 key) external;
    function revealPhaseEnded(uint gameID) external;
    function balanceOf(address player) external view returns (uint);
    function withdraw(uint amount) external;
}

contract RPS is IRPS {
    // This contract lets players play rock-paper-scissors.
    // its constructor receives a uint k which is the number of blocks mined before a reveal phase is over.

    // players can send the contract money to fund their bets, see their balance and withdraw it, as long as the amount is not in an active game.

    // the game mechanics: The players choose a gameID (some uint) that is not being currently used. They then each call make_move() making a bet and committing to a move.
    // in the next phase each of them reveals their committment, and once the second commit is done, the game is over. The winner gets the amount of money they agreed on.

    //TODO: add state variables and additional functions as needed.

    // State variables
    uint public revealPeriodLength;
    mapping(uint => Game) public games;
    mapping(address => uint) public playerBalances;

    // Game struct to track game state
    struct Game {
        address player1;
        address player2;
        bytes32 commitment1;
        bytes32 commitment2;
        Move move1;
        Move move2;
        uint betAmount;
        uint revealBlock;
        GameState state;
    }

    constructor(uint _revealPeriodLength) {
        require(_revealPeriodLength >= 1, "Reveal period must be at least 1 block");
        revealPeriodLength = _revealPeriodLength;
    }

    function checkCommitment(
        bytes32 commitment,
        Move move,
        bytes32 key
    ) public pure returns (bool) {
        return keccak256(abi.encodePacked(move, key)) == commitment;
    }

    function makeMove(uint gameID, uint betAmount, bytes32 hiddenMove) external {
        // Ensure game doesn't already exist or is not in progress
        require(games[gameID].state == GameState.NO_GAME || games[gameID].state == GameState.MOVE1, "Game already in progress");
        
        // Player must have sufficient balance
        require(playerBalances[msg.sender] >= betAmount, "Insufficient balance");

        // First player to make a move
        if (games[gameID].player1 == address(0)) {
            games[gameID] = Game({
                player1: msg.sender,
                player2: address(0),
                commitment1: hiddenMove,
                commitment2: bytes32(0),
                move1: Move.NONE,
                move2: Move.NONE,
                betAmount: betAmount,
                revealBlock: 0,
                state: GameState.MOVE1
            });
            
            // Deduct bet from player's balance
            playerBalances[msg.sender] -= betAmount;
        } 
        // Second player to make a move
        else if (games[gameID].state == GameState.MOVE1) {
            require(msg.sender != games[gameID].player1, "Cannot play against yourself");
            
            games[gameID].player2 = msg.sender;
            games[gameID].commitment2 = hiddenMove;
            games[gameID].state = GameState.MOVE2;
            
            // Deduct bet from player's balance
            playerBalances[msg.sender] -= betAmount;
        } else {
            revert("Invalid game state");
        }
    }

    function cancelGame(uint gameID) external {
        Game storage game = games[gameID];
        
        // Can only cancel if only first player has made a move
        require(game.state == GameState.MOVE1, "Cannot cancel this game");
        require(msg.sender == game.player1, "Only player1 can cancel");
        
        // Refund player's bet
        playerBalances[msg.sender] += game.betAmount;
        
        // Reset game state
        delete games[gameID];
    }

    function revealMove(uint gameID, Move move, bytes32 key) external {
        Game storage game = games[gameID];
        
        // Ensure game is in correct state
        require(game.state == GameState.MOVE1 || game.state == GameState.MOVE2, "Invalid game state for reveal");
        
        // Verify player's move matches their commitment
        if (msg.sender == game.player1) {
            require(checkCommitment(game.commitment1, move, key), "Invalid move commitment");
            game.move1 = move;
        } else if (msg.sender == game.player2) {
            require(checkCommitment(game.commitment2, move, key), "Invalid move commitment");
            game.move2 = move;
        } else {
            revert("Not a player in this game");
        }
        
        // Update game state
        if (game.move1 != Move.NONE && game.move2 != Move.NONE) {
            game.state = GameState.REVEAL1;
            game.revealBlock = block.number;
            
            // Determine winner
            address winner = determineWinner(gameID);
            
            // Distribute funds
            if (winner == address(0)) {
                // Tie: return bets to both players
                playerBalances[game.player1] += game.betAmount;
                playerBalances[game.player2] += game.betAmount;
            } else {
                playerBalances[winner] += 2 * game.betAmount;
            }
        }
    }

    function determineWinner(uint gameID) internal view returns (address) {
        Game storage game = games[gameID];
        
        // Determine winner based on rock-paper-scissors rules
        if (game.move1 == game.move2) return address(0); // Tie
        
        if (
            (game.move1 == Move.ROCK && game.move2 == Move.SCISSORS) ||
            (game.move1 == Move.PAPER && game.move2 == Move.ROCK) ||
            (game.move1 == Move.SCISSORS && game.move2 == Move.PAPER)
        ) {
            return game.player1;
        }
        
        return game.player2;
    }

    function revealPhaseEnded(uint gameID) external {
        Game storage game = games[gameID];
        
        // Ensure game is in reveal phase
        require(game.state == GameState.REVEAL1, "Cannot end reveal phase");
        
        // Check if enough blocks have passed
        require(block.number >= game.revealBlock + revealPeriodLength, "Reveal phase not ended");
        
        // If one player didn't reveal, the other wins
        if (game.move1 == Move.NONE) {
            playerBalances[game.player2] += 2 * game.betAmount;
            game.state = GameState.LATE;
        } else if (game.move2 == Move.NONE) {
            playerBalances[game.player1] += 2 * game.betAmount;
            game.state = GameState.LATE;
        }
    }

    function getGameState(uint gameID) external view returns (GameState) {
        return games[gameID].state;
    }

    function balanceOf(address player) external view returns (uint) {
        return playerBalances[player];
    }

    function withdraw(uint amount) external {
        require(playerBalances[msg.sender] >= amount, "Insufficient balance");
        playerBalances[msg.sender] -= amount;
        payable(msg.sender).transfer(amount);
    }

    // Fallback function to allow depositing funds
    receive() external payable {
        playerBalances[msg.sender] += msg.value;
    }
}
