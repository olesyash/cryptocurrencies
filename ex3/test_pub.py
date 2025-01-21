import eth_typing
from web3.types import Wei
from web3 import Web3
from logger import logger
import secrets
import pytest
from typing import Any, Tuple
import web3.contract
import solcx  # type: ignore

# run the line below to install the compiler ->  only once is needed.
solcx.install_solc(version='0.8.19')

def compile(file_name: str) -> Any:
    # set the version
    solcx.set_solc_version('0.8.19')

    # compile
    compiled_sol = solcx.compile_files(
        [file_name], output_values=['abi', 'bin'])

    # retrieve the contract interface
    contract_id, contract_interface = compiled_sol.popitem()
    return contract_interface['bin'], contract_interface['abi']

REVEAL_TIME: int = 5
ONE_ETH = 10**18

ROCK = 1
PAPER = 2
SCISSORS = 3

NO_GAME = 0
MOVE1 = 1
MOVE2 = 2
REVEAL1 = 3
LATE = 4

Account = eth_typing.ChecksumAddress
Accounts = Tuple[Account, ...]
RevertException = web3.exceptions.ContractLogicError

def check_send_money(w3: Web3, from_addr: Account, to_addr: Account, amount: int) -> None:
    """send money from one account to another and check if the transaction is successful"""
    logger.info(f"Sending {amount} wei from {from_addr} to {to_addr}")
    tx_hash = w3.eth.send_transaction({
        'to': to_addr,
        'from': from_addr,
        'value': Wei(amount)
    })
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    logger.info(
        f"Transaction receipt received. Status: {tx_receipt['status']}")
    assert tx_receipt["status"] == 1

def deploy_compiled_contract(w3: Web3, bytecode: str, abi: Any, from_account: Account, *args: Any) -> web3.contract.Contract:
    """Deploy a compiled contract"""
    logger.info("Deploying the contract")
    contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    ctor = contract.constructor(*args)
    logger.info(f"sending the deployment transaction from {from_account}")
    tx_hash = ctor.transact({'from': from_account})

    logger.info(
        f"Waiting for the transaction receipt of the deployment transaction {tx_hash}")
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    assert tx_receipt["status"] == 1

    logger.info(f"Contract deployed at {tx_receipt['contractAddress']}")
    deployed_contract = w3.eth.contract(
        address=tx_receipt["contractAddress"], abi=abi)

    return deployed_contract

class RPS:
    def __init__(self, w3: Web3, rps_contract: web3.contract.Contract) -> None:
        self.w3 = w3
        self.contract = rps_contract

    @property
    def address(self) -> Account:
        return Account(self.contract.address)

    def get_game_state(self, game_id: int) -> int:
        logger.info(f"Calling RPS.get_game_state[{game_id}]")
        state = int(self.contract.functions.getGameState(game_id).call())
        logger.info(f"State is {state}")
        return state

    def withdraw(self, amount: int, from_account: Account) -> None:
        logger.info(
            f"Calling RPS.withdraw to withdraw {amount} from {from_account}")
        tx_hash = self.contract.functions.withdraw(
            amount).transact({'from': from_account})
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        assert tx_receipt["status"] == 1

    def make_move(self, game_id: int, bet_ammount: int, move_commit: bytes, from_account: Account) -> None:
        logger.info(
            f"Calling RPS.makeMove with bet {bet_ammount} in game {game_id} from {from_account}")
        tx_hash = self.contract.functions.makeMove(game_id, bet_ammount, move_commit).transact(
            {'from': from_account})
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        assert tx_receipt["status"] == 1

    def reveal_move(self, game_id: int, move: int, key: bytes, from_account: Account) -> None:
        logger.info(
            f"Calling RPS.revealMove with move {move} in game {game_id} from {from_account}")
        tx_hash = self.contract.functions.revealMove(
            game_id, move, key).transact({'from': from_account})
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        assert tx_receipt["status"] == 1

    def cancel_game(self, game_id: int, from_account: Account) -> None:
        logger.info(
            f"Calling RPS.cancelGame with game id {game_id} from {from_account}")
        tx_hash = self.contract.functions.cancelGame(game_id).transact(
            {'from': from_account})
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        assert tx_receipt["status"] == 1

    def reveal_phase_ended(self, game_id: int, from_account: Account) -> None:
        logger.info(
            f"Calling RPS.revealPhaseEnded for game {game_id} from {from_account}")
        tx_hash = self.contract.functions.revealPhaseEnded(game_id).transact(
            {'from': from_account})
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        assert tx_receipt["status"] == 1

    def balance_of(self, x: Account) -> int:
        return int(self.contract.functions.balanceOf(x).call())

@pytest.fixture(scope="module")
def w3():
    # Connect to local Ethereum node (Ganache)
    w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:8545'))
    assert w3.is_connected(), "Failed to connect to the Ethereum network"
    return w3

@pytest.fixture(scope="module")
def accounts(w3):
    return w3.eth.accounts

@ pytest.fixture(scope="module")
def rps(w3: Web3, accounts: Accounts) -> RPS:
    logger.info("Preparing the RPS contract")
    
    rps_file_path = "part1/hardhat-project/contracts/RPS.sol"
    bytecode, abi = compile(rps_file_path)

    logger.info("Compiled. Now deploying the RPS contract")
    from_account = accounts[9]
    rps_contract = deploy_compiled_contract(
        w3, bytecode, abi, from_account, REVEAL_TIME)
    return RPS(w3, rps_contract)


@ pytest.fixture(scope="module")
def alice(w3: Web3, rps: RPS, accounts: Accounts) -> Account:
    logger.info("Sending 1 ether from alice to the RPS contract")
    check_send_money(w3, accounts[0], rps.address, ONE_ETH)
    return accounts[0]

@ pytest.fixture(scope="module")
def bob(w3: Web3, rps: RPS, accounts: Accounts) -> Account:
    logger.info("Sending 1 ether from bob to the RPS contract")
    check_send_money(w3, accounts[1], rps.address, ONE_ETH)
    return accounts[1]

@ pytest.fixture(scope="module")
def charlie(w3: Web3, rps: RPS, accounts: Accounts) -> Account:
    logger.info("Sending 1 ether from charlie to the RPS contract")
    check_send_money(w3, accounts[2], rps.address, ONE_ETH)
    return accounts[2]

def get_commit(data: int, key: bytes) -> bytes:
    return Web3.solidity_keccak(['uint8', 'bytes32'], [data, key])


# Test: happy flow
def test_two_game_flow(rps: RPS, alice: Any, bob: Any, charlie: Any) -> None:
    moves = [ROCK, PAPER, SCISSORS, ROCK]
    keys = [secrets.token_bytes(32) for _ in moves]
    commits = [get_commit(move, key) for move, key in zip(moves, keys)]

    rps.make_move(1337, ONE_ETH//1024, commits[0], from_account=alice)
    rps.make_move(17, ONE_ETH//1024, commits[2], from_account=alice)
    assert rps.get_game_state(1337) == MOVE1
    assert rps.get_game_state(17) == MOVE1
    rps.make_move(1337, ONE_ETH//1024, commits[1], from_account=bob)
    rps.make_move(17, ONE_ETH//1024, commits[3], from_account=charlie)
    assert rps.get_game_state(1337) == MOVE2
    assert rps.get_game_state(17) == MOVE2

    rps.reveal_move(1337, moves[0], keys[0], from_account=alice)
    rps.reveal_move(17, moves[2], keys[2], from_account=alice)
    assert rps.get_game_state(1337) == REVEAL1
    assert rps.get_game_state(17) == REVEAL1

    rps.reveal_move(1337, moves[1], keys[1], from_account=bob)
    rps.reveal_move(17, moves[3], keys[3], from_account=charlie)
    assert rps.get_game_state(1337) == NO_GAME
    assert rps.get_game_state(17) == NO_GAME

# Test: Requirement - bet can't be negative
def test_invalid_bet(rps: RPS, alice: Any) -> None:
    invalid_bet = -1  # Invalid bet amount
    move = ROCK
    key = secrets.token_bytes(32)
    commit = get_commit(move, key)
    with pytest.raises(Exception):
        rps.make_move(1, invalid_bet, commit, from_account=alice)
    
    """Requirement - cancelGame can run only in MOVE1 state"""
    with pytest.raises(RevertException):
        rps.cancel_game(1, alice)

# Test: Requirement - first call of revealMove can be made only after two moves are entered
def test_early_reveal(rps: RPS, alice: Any) -> None:
    move = ROCK
    key = secrets.token_bytes(32)
    commit = get_commit(move, key)

    rps.make_move(1, ONE_ETH//1024, commit, from_account=alice)
    with pytest.raises(RevertException):
        rps.reveal_move(1, move, key, from_account=alice)
    
    rps.cancel_game(1, alice)

# Test: Requirement - withdraws amount from the account of the sender
def test_withdraw(rps: RPS, alice: Any) -> None:
    initial_balance = rps.balance_of(alice)
    assert initial_balance > 0
    withdraw_amount = initial_balance // 2

    rps.withdraw(withdraw_amount, from_account=alice)
    new_balance = rps.balance_of(alice)
    assert new_balance == initial_balance - withdraw_amount

# Test: Requirement - can't withdraw more than balance
def test_insufficient_funds_to_withdraw(rps: RPS, alice: Any) -> None:
    initial_balance = rps.balance_of(alice)
    with pytest.raises(RevertException):
        rps.withdraw(initial_balance*2, from_account=alice)
    
    """Requirement - funds currently staked in a game are unavailable"""
    move = ROCK
    key = secrets.token_bytes(32)
    commit = get_commit(move, key)
    rps.make_move(1, ONE_ETH//1024, commit, from_account=alice)
    with pytest.raises(RevertException):
        rps.withdraw(initial_balance, from_account=alice)
    rps.cancel_game(1, from_account=alice)

# Test: Requirement - getGameState must return the correct state of the game.
def test_get_game_state_initial(rps: RPS) -> None:
    """Requirement: getGameState should return NO_GAME for unused game IDs."""
    assert rps.get_game_state(9999) == NO_GAME

# Test: Requirement - makeMove should initialize a game and record the player's move.
def test_make_move(rps: RPS, alice: Any) -> None:
    """Requirement: makeMove initializes a game and locks funds for the first player."""
    move = ROCK
    key = secrets.token_bytes(32)
    commit = get_commit(move, key)

    initial_balance = rps.balance_of(alice)
    rps.make_move(1, ONE_ETH//1024, commit, from_account=alice)
    assert rps.get_game_state(1) == MOVE1
    new_balance = rps.balance_of(alice)
    assert new_balance == initial_balance - ONE_ETH//1024

    rps.cancel_game(1, alice)

# Test: Requirement - cancelGame should cancel a game if only one player has committed.
def test_cancel_game(rps: RPS, alice: Any, bob: Any) -> None:
    """Requirement: cancelGame should return funds if only one move was made."""
    move = PAPER
    alice_key = secrets.token_bytes(32)
    alice_commit = get_commit(move, alice_key)
    
    bob_key = secrets.token_bytes(32)
    bob_commit = get_commit(move, bob_key)
    
    alice_initial_balance = rps.balance_of(alice)
    bob_initial_balance = rps.balance_of(bob)

    rps.make_move(1, ONE_ETH//1024, alice_commit, from_account=alice)
    rps.cancel_game(1, from_account=alice)
    assert rps.get_game_state(1) == NO_GAME

    rps.make_move(1, ONE_ETH//1024, alice_commit, from_account=alice)
    rps.make_move(1, ONE_ETH//1024, bob_commit, from_account=bob)
    assert rps.get_game_state(1) == MOVE2
    with pytest.raises(RevertException):
        rps.cancel_game(1, from_account=alice)
    with pytest.raises(RevertException):
        rps.cancel_game(1, from_account=bob)
    
    """balances should be restored if draw"""
    rps.reveal_move(1, move, alice_key, from_account=alice)
    rps.reveal_move(1, move, bob_key, from_account=bob)
    assert alice_initial_balance == rps.balance_of(alice)
    assert bob_initial_balance == rps.balance_of(bob)
    assert rps.get_game_state(1) == NO_GAME

# Test: Requirement - revealMove should validate the move and key against the commitment.
def test_reveal_move(rps: RPS, alice: Any, bob: Any, charlie: Any) -> None:
    """Requirement: revealMove validates commitments and transitions game state."""
    move1, move2 = ROCK, SCISSORS
    key1, key2 = secrets.token_bytes(32), secrets.token_bytes(32)
    commit1, commit2 = get_commit(move1, key1), get_commit(move2, key2)

    alice_initial_balance = rps.balance_of(alice)
    rps.make_move(1, ONE_ETH//1024, commit1, from_account=alice)
    rps.make_move(1, ONE_ETH//1024, commit2, from_account=bob)
    rps.reveal_move(1, move2, key2, from_account=bob)
    assert rps.get_game_state(1) == REVEAL1
    with pytest.raises(RevertException):
        rps.reveal_move(1, move2, key2, from_account=bob)
    with pytest.raises(RevertException):
        rps.reveal_move(1, move2, key2, from_account=charlie)
    
    rps.reveal_move(1, move1, key1, from_account=alice)
    alice_new_balance = rps.balance_of(alice)
    assert alice_new_balance == alice_initial_balance + ONE_ETH//1024
    assert rps.get_game_state(1) == NO_GAME

# Test: Requirement - The amount provided by the second player is ignored
def test_ignore_second_bet(rps: RPS, alice: Any, bob: Any) -> None:
    move1, move2 = ROCK, SCISSORS
    key1, key2 = secrets.token_bytes(32), secrets.token_bytes(32)
    commit1, commit2 = get_commit(move1, key1), get_commit(move2, key2)

    bob_initial_balance = rps.balance_of(bob)
    assert bob_initial_balance > 0
    bob_bet = bob_initial_balance * 2 # shouldn't raise an error

    rps.make_move(1, ONE_ETH//1024, commit1, from_account=alice)
    rps.make_move(1, bob_bet, commit2, from_account=bob)
    assert rps.get_game_state(1) == MOVE2
    
    new_balance = rps.balance_of(bob)
    assert new_balance == bob_initial_balance - ONE_ETH//1024

    rps.reveal_move(1, move1, key1, from_account=alice)
    rps.reveal_move(1, move2, key2, from_account=bob)
    assert rps.get_game_state(1) == NO_GAME

# Test: Requirement - revealPhaseEnded should allow claiming funds if the opponent is late.
def test_reveal_phase_ended(w3: Web3, rps: RPS, alice: Any, bob: Any, charlie: Any) -> None:
    """Requirement: revealPhaseEnded allows the first revealer to claim funds."""
    move1, move2 = ROCK, SCISSORS
    key1, key2 = secrets.token_bytes(32), secrets.token_bytes(32)
    commit1, commit2 = get_commit(move1, key1), get_commit(move2, key2)

    bob_initial_balance = rps.balance_of(bob)
    rps.make_move(1, ONE_ETH//1024, commit1, from_account=alice)
    rps.make_move(1, ONE_ETH//1024, commit2, from_account=bob)
    rps.reveal_move(1, move2, key2, from_account=bob)
    assert rps.get_game_state(1) == REVEAL1
    with pytest.raises(RevertException):
        rps.reveal_phase_ended(1, from_account=bob)
    with pytest.raises(RevertException):
        rps.reveal_phase_ended(1, from_account=alice)
    with pytest.raises(RevertException):
        rps.reveal_phase_ended(1, from_account=charlie)
    assert rps.get_game_state(1) == REVEAL1
    
    for i in range(REVEAL_TIME):
        rps.make_move(10+i, ONE_ETH//2048, commit2, from_account=bob)
        rps.cancel_game(10+i, from_account=bob)
    
    assert rps.get_game_state(1) == REVEAL1
    rps.reveal_phase_ended(1, from_account=bob)
    bob_new_balance = rps.balance_of(bob)
    assert bob_new_balance == bob_initial_balance + ONE_ETH//1024
    assert rps.get_game_state(1) == NO_GAME
