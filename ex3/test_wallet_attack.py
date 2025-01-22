from web3 import Web3
import eth_typing
from web3.types import Wei
import pytest
from typing import Any, Tuple
import web3.contract
import solcx  # type: ignore

# Install solc compiler
solcx.install_solc(version='0.8.19')

ONE_ETH = 10**18
Account = eth_typing.ChecksumAddress
Accounts = Tuple[Account, ...]
RevertException = web3.exceptions.ContractLogicError

def compile(file_name: str) -> Any:
    # Set the version
    solcx.set_solc_version('0.8.19')

    # Create full path
    contract_path = f"part1/hardhat-project/contracts/{file_name}"
    
    # Compile
    compiled_sol = solcx.compile_files(
        [contract_path],
        output_values=['abi', 'bin']
    )

    # Get the contract name from the file path
    contract_name = file_name.replace('.sol', '')
    contract_id = f"{contract_path}:{contract_name}"
    
    # For Wallet contract, the class name is just "Wallet"
    if contract_name == "VulnerableWallet":
        contract_id = f"{contract_path}:Wallet"

    # Get the contract interface
    contract_interface = compiled_sol[contract_id]
    return contract_interface['bin'], contract_interface['abi']

def deploy_contract(w3: Web3, bytecode: str, abi: Any, from_account: Account, *args: Any) -> web3.contract.Contract:
    """Deploy a compiled contract"""
    contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    ctor = contract.constructor(*args)
    tx_hash = ctor.transact({'from': from_account})
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    assert tx_receipt["status"] == 1
    deployed_contract = w3.eth.contract(
        address=tx_receipt["contractAddress"], abi=abi)
    return deployed_contract

class WalletAttack:
    def __init__(self, w3: Web3, contract: web3.contract.Contract) -> None:
        self.w3 = w3
        self.contract = contract

    @property
    def address(self) -> Account:
        return Account(self.contract.address)

    def exploit(self, target_address: Account, value: int, from_account: Account) -> None:
        # Call the exploit function on the contract
        tx_hash = self.contract.functions.exploit(target_address).transact(
            {'from': from_account, 'value': value})
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        assert tx_receipt["status"] == 1

class Wallet:
    def __init__(self, w3: Web3, contract: web3.contract.Contract) -> None:
        self.w3 = w3
        self.contract = contract

    @property
    def address(self) -> Account:
        return Account(self.contract.address)

    def deposit(self, value: int, from_account: Account) -> None:
        tx_hash = self.contract.functions.deposit().transact(
            {'from': from_account, 'value': value})
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        assert tx_receipt["status"] == 1

    def get_balance(self, from_account: Account) -> int:
        return self.contract.functions.getBalance().call({'from': from_account})

    def send_to(self, destination: Account, from_account: Account) -> None:
        tx_hash = self.contract.functions.sendTo(destination).transact(
            {'from': from_account})
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        assert tx_receipt["status"] == 1

@pytest.fixture(scope="module")
def w3():
    # Connect to local Ethereum node (Ganache)
    w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:8545'))
    assert w3.is_connected(), "Failed to connect to the Ethereum network"
    return w3

@pytest.fixture(scope="module")
def accounts(w3):
    return w3.eth.accounts

@pytest.fixture(scope="module")
def wallet(w3: Web3, accounts: Accounts) -> Wallet:
    # Deploy the vulnerable wallet contract
    bytecode, abi = compile("VulnerableWallet.sol")
    contract = deploy_contract(w3, bytecode, abi, accounts[0])
    return Wallet(w3, contract)

@pytest.fixture(scope="module")
def wallet_attack(w3: Web3, accounts: Accounts) -> WalletAttack:
    # Deploy the wallet attack contract
    bytecode, abi = compile("WalletAttack.sol")
    contract = deploy_contract(w3, bytecode, abi, accounts[0])
    return WalletAttack(w3, contract)

@pytest.fixture(scope="module")
def attacker(accounts: Accounts) -> Account:
    return accounts[1]

@pytest.fixture(scope="module")
def victim(accounts: Accounts) -> Account:
    return accounts[2]

def test_wallet_attack(w3: Web3, wallet: Wallet, wallet_attack: WalletAttack, attacker: Account, victim: Account):
    """Test the reentrancy attack on the vulnerable wallet"""
    
    # First, let's fund the vulnerable wallet with 5 ETH from the victim
    victim_initial_balance = w3.eth.get_balance(victim)
    wallet.deposit(5 * ONE_ETH, from_account=victim)
    assert w3.eth.get_balance(wallet.address) == 5 * ONE_ETH
    assert wallet.get_balance(from_account=victim) == 5 * ONE_ETH

    # Now perform the attack with 1 ETH
    attacker_initial_balance = w3.eth.get_balance(attacker)
    wallet_attack.exploit(wallet.address, ONE_ETH, from_account=attacker)

    # Check that the attack was successful:
    # 1. Wallet should be drained (balance should be 0)
    assert w3.eth.get_balance(wallet.address) == 0
    
    # The victim's balance in the mapping will still be 5 ETH
    # but they can't withdraw it because there's no ETH left
    victim_balance = wallet.get_balance(from_account=victim)
    assert victim_balance == 5 * ONE_ETH
    
    # Try to withdraw the victim's balance - this should fail
    with pytest.raises(RevertException):
        wallet.send_to(attacker, from_account=victim)

    # 2. Attacker should have gained at least 3 ETH (minus gas costs)
    attacker_profit = w3.eth.get_balance(attacker) - attacker_initial_balance
    assert attacker_profit >= 3 * ONE_ETH - ONE_ETH  # At least 2 ETH profit (considering 1 ETH cost)

    # 3. Victim should have lost their 5 ETH deposit
    assert wallet.get_balance(from_account=victim) == 5 * ONE_ETH
