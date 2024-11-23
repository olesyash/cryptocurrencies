from . import bank
from .utils import *
from .transaction import Transaction
from .bank import Bank
from typing import Optional, List


class Wallet:
    def __init__(self) -> None:
        """This function generates a new wallet with a new private key."""
        self.private_key, self.public_key = gen_keys()
        self.utxos: List[TxID] = []  # Track UTxOs owned by the wallet.
        self.frozen_utxos: List[TxID] = []  # UTxOs lock by pending transactions.
        self.last_block_hash: Optional[BlockHash] = None

    def update(self, bank: Bank) -> None:
        """
        This function updates the balance allocated to this wallet by querying the bank.
        Don't read all of the bank's utxo, but rather process the blocks since the last update one at a time.
        For this exercise, there is no need to validate all transactions in the block.
        """
        index = 0
        if self.last_block_hash:
            #  Search for the index of the last processed block in the blockchain
            for i, block in enumerate(bank.blockchain):
                if block.get_block_hash() == self.last_block_hash:
                    index = i + 1
                    break

        for block in bank.blockchain[index:]:
            for tx in block.get_transactions():
                if tx.output == self.get_address():
                    # Add new UTxOs that belong to this wallet
                    self.utxos.append(tx.get_txid())
                # Remove spent UTxOs
                if tx.input in self.utxos:
                    self.utxos.remove(tx.input)

            self.last_block_hash = block.get_block_hash()

    def create_transaction(self, target: PublicKey) -> Optional[Transaction]:
        """
        This function returns a signed transaction that moves an unspent coin to the target.
        It chooses the coin based on the unspent coins that this wallet had since the last update.
        If the wallet already spent a specific coin, but that transaction wasn't confirmed by the
        bank just yet (it still wasn't included in a block) then the wallet  shouldn't spend it again
        until unfreeze_all() is called. The method returns None if there are no unspent outputs that can be used.
        """

    def unfreeze_all(self) -> None:
        """
        Allows the wallet to try to re-spend outputs that it created transactions for (unless these outputs made it into the blockchain).
        """
        self.frozen_utxos.clear()

    def get_balance(self) -> int:
        """
        This function returns the number of coins that this wallet has.
        It will return the balance according to information gained when update() was last called.
        Coins that the wallet owned and sent away will still be considered as part of the balance until the spending
        transaction is in the blockchain.
        """
        return len(self.utxos)

    def get_address(self) -> PublicKey:
        """
        This function returns the public address of this wallet (see the utils module for generating keys).
        """
        return self.public_key
