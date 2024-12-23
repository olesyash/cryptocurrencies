from . import bank
from .utils import *
from .transaction import Transaction
from .bank import Bank
from typing import Optional, List


class Wallet:
    def __init__(self) -> None:
        """This function generates a new wallet with a new private key."""
        self.private_key, self.public_key = gen_keys()
        self.utxos: List[Transaction] = []  # Track UTxOs owned by the wallet.
        self.frozen_utxos: List[Transaction] = []  # UTxOs lock by pending transactions.
        self.last_block_hash: Optional[BlockHash] = None

    def update(self, bank: Bank) -> None:
        """
        This function updates the balance allocated to this wallet by querying the bank.
        Don't read all of the bank's utxo, but rather process the blocks since the last update one at a time.
        For this exercise, there is no need to validate all transactions in the block.
        """
        index = 0
        if self.last_block_hash:
            for i, block in enumerate(bank.blockchain):
                if block.get_block_hash() == self.last_block_hash:
                    index = i + 1
                    break

        # Store full transactions, not just IDs
        for block in bank.blockchain[index:]:
            for tx in block.get_transactions():
                if tx.output == self.get_address():
                    # Store the full transaction, not just its ID
                    self.utxos.append(tx)

                # Remove spent UTxOs
                # Now check against full transactions
                self.utxos = [utxo for utxo in self.utxos if utxo.get_txid() != tx.input]
                self.frozen_utxos = [f_utxo for f_utxo in self.frozen_utxos if f_utxo != tx.input]

            self.last_block_hash = block.get_block_hash()

    def create_transaction(self, target: PublicKey) -> Optional[Transaction]:
        """
        This function returns a signed transaction that moves an unspent coin to the target.
        It chooses the coin based on the unspent coins that this wallet had since the last update.
        If the wallet already spent a specific coin, but that transaction wasn't confirmed by the
        bank just yet (it still wasn't included in a block) then the wallet  shouldn't spend it again
        until unfreeze_all() is called. The method returns None if there are no unspent outputs that can be used.
        """
        # Retrieve the list of unspent transactions (UTXOs) from the bank
        # Find an unspent transaction that belongs to this wallet
        for utxo in self.utxos:
            if utxo not in self.frozen_utxos:
                self.frozen_utxos.append(utxo)
                # Sign the transaction with the wallet's private key
                message = utxo.get_txid() + target
                signature = sign(message, self.private_key)
                # Create a new transaction using the unspent transaction
                new_tx = Transaction(target, utxo.get_txid(), signature)
                return new_tx

        # Return None if there are no unspent outputs that can be used
        return None

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
