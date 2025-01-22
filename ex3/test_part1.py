import eth_typing
from web3.types import Wei
from web3 import Web3
import pytest
from typing import Any, Tuple
import web3.contract
import solcx  # type: ignore

# run the line below to install the compiler ->  only once is needed.
solcx.install_solc(version='0.8.19')

ONE_ETH = 10**18

def compile(file_name: str, contract_name: str) -> Any:
    # set the version
    solcx.set_solc_version('0.8.19')

    # compile
    compiled_sol = solcx.compile_files(
        [file_name], output_values=['abi', 'bin'])

    # retrieve the contract interface
    contract_interface = compiled_sol[f"{file_name}:{contract_name}"]
    return contract_interface['bin'], contract_interface['abi']

Account = eth_typing.ChecksumAddress
Accounts = Tuple[Account, ...]
RevertException = web3.exceptions.ContractLogicError

def deploy_compiled_contract(w3: Web3, bytecode: str, abi: Any, from_account: Account, *args: Any) -> web3.contract.Contract:
    """Deploy a compiled contract"""
    contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    tx = contract.constructor(*args).transact({'from': from_account})
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx)
    assert tx_receipt["status"] == 1
    return w3.eth.contract(address=tx_receipt["contractAddress"], abi=abi)


class VUL:
    def __init__(self, w3: Web3, vul_contract: web3.contract.Contract) -> None:
        self.w3 = w3
        self.contract = vul_contract
        self.abi = vul_contract.abi

    @property
    def address(self) -> Account:
        return Account(self.contract.address)
    
    def deposit(self, from_account: Account, amount: int) -> None:
        tx_hash = self.contract.functions.deposit.transact({'from': from_account, 'value': amount})
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        assert tx_receipt["status"] == 1

    def send_to(self, from_account: Account, to_account: Account) -> None:
        tx_hash = self.contract.functions.sendTo(
            to_account).transact({'from': from_account})
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        assert tx_receipt["status"] == 1


class ATK:
    def __init__(self, w3: Web3, atk_contract: web3.contract.Contract, attacker: Account) -> None:
        self.w3 = w3
        self.contract = atk_contract
        self.attacker = attacker
        self.abi = atk_contract.abi

    @property
    def address(self) -> Account:
        return Account(self.contract.address)

    def attack(self, vul_contract: Account) -> bool:
        tx_hash = self.contract.functions.exploit(vul_contract).transact({
            'from': self.attacker,
            'value': ONE_ETH,
            'gas': 3000000
            })
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        assert tx_receipt["status"] == 1
        return True



@pytest.fixture(scope="module")
def w3():
    # Connect to local Ethereum node (Ganache)
    w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:8545'))
    assert w3.is_connected(), "Failed to connect to the Ethereum network"
    return w3

@pytest.fixture(scope="module")
def accounts(w3):
    return w3.eth.accounts

# Deploy contrats
@pytest.fixture(scope="module")
def wallet_attack(w3, accounts):
    bytecode, abi = compile("part1/hardhat-project/contracts/WalletAttack.sol", "WalletAttack")
    attacker_account = accounts[0]

    attacker_contract = deploy_compiled_contract(
        w3, bytecode, abi, attacker_account)
    return ATK(w3, attacker_contract, attacker_account)

# Deploy contrats
@pytest.fixture(scope="module")
def vulnerable_wallet(w3, accounts):
    bytecode, abi = compile("part1/hardhat-project/contracts/VulnerableWallet.sol", "Wallet")
    victim_account = accounts[9]

    vulnerable_contract = deploy_compiled_contract(
        w3, bytecode, abi, victim_account)
    return VUL(w3, vulnerable_contract)


# Test: happy flow
def test_attack_and_get_3_ether(w3: Web3, vulnerable_wallet: VUL, wallet_attack: ATK, accounts: Accounts) -> None:
    attacker = accounts[0]
    victim = accounts[9]
    print(f"\nvulnerable_contract address: {vulnerable_wallet.address}")
    print(f"attack_contract address: {wallet_attack.address}")
    print(f"Vulnerable wallet balance: {w3.from_wei(w3.eth.get_balance(vulnerable_wallet.address), 'ether')}")
    vulnerable_wallet.deposit(victim, 5 * ONE_ETH)
    print(f"deposit succesfull.\nNew vulnerable wallet balance: {w3.from_wei(w3.eth.get_balance(vulnerable_wallet.address), 'ether')}")
    balance_before = w3.from_wei(w3.eth.get_balance(attacker), 'ether')
    print(f"Attacker balance before attack: {balance_before}")
    result = wallet_attack.attack(vulnerable_wallet.address)
    assert result == True
    balance_after = w3.from_wei(w3.eth.get_balance(attacker), 'ether')
    print(f"vulnerable wallet balance after attack: {w3.from_wei(w3.eth.get_balance(vulnerable_wallet.address), 'ether')}")
    print(f"Attacker balance after attack: {balance_after}")
    assert balance_after - balance_before >= 3
