import secrets

from .utils import BlockHash, PublicKey
from .transaction import Transaction
from .block import Block
from typing import List
from .utils import *

class Bank:
    def __init__(self) -> None:
        """Creates a bank with an empty blockchain and an empty mempool."""
        self.mem_pool: List[Transaction] = []
        self.blockchain: List[Block] = []

    def add_transaction_to_mempool(self, transaction: Transaction) -> bool:
        """
        This function inserts the given transaction to the mempool.
        It will return False if one of the following conditions hold:
        (i) the transaction is invalid (the signature fails)
        (ii) the source doesn't have the coin that he tries to spend
        (iii) there is contradicting tx in the mempool.
        (iv) there is no input (i.e., this is an attempt to create money from nothing)
        """
        # Check if the transaction is valid (signature verification)
        if not verify(transaction.input, transaction.signature, transaction.output):
            return False

        # Check for contradicting transactions in the mempool
        for tx in self.mem_pool:
            if tx.input == transaction.input:
                return False

        # Check if there is no input (attempt to create money from nothing)
        if transaction.input is None:
            return False

        self.mem_pool.append(transaction)
        return True

    def end_day(self, limit: int = 10) -> BlockHash:
        """
        This function tells the bank that the day ended,
        and that the first `limit` transactions in the mempool should be committed to the blockchain.
        If there are fewer than 'limit' transactions in the mempool, a smaller block is created.
        If there are no transactions, an empty block is created. The hash of the block is returned.
        """
        transactions = self.mem_pool[:limit]
        self.mem_pool = self.mem_pool[limit:]
        block = Block(transactions, self.get_latest_hash())
        self.blockchain.append(block)
        return block.get_block_hash()

    def get_block(self, block_hash: BlockHash) -> Block:
        """
        This function returns a block object given its hash. If the block doesnt exist, an exception is thrown..
        """
        for block in self.blockchain:
            if block.get_block_hash() == block_hash:
                return block

    def get_latest_hash(self) -> BlockHash:
        """
        This function returns the hash of the last Block that was created by the bank.
        """
        return self.blockchain[-1].get_block_hash()

    def get_mempool(self) -> List[Transaction]:
        """
        This function returns the list of transactions that didn't enter any block yet.
        """
        return self.mem_pool

    def get_utxo(self) -> List[Transaction]:
        """
        This function returns the list of unspent transactions.
        """
        utxos = []
        spent_txids = set()

        # Iterate through all blocks in the blockchain
        for block in self.blockchain:
            for tx in block.transactions:
                # If the transaction has an input, mark it as spent
                if tx.input:
                    spent_txids.add(tx.input)
                # Add the transaction to UTXOs if it is not spent
                if tx.get_txid() not in spent_txids:
                    utxos.append(tx)

        return utxos

    def create_money(self, target: PublicKey) -> None:
        """
        This function inserts a transaction into the mempool that creates a single coin out of thin air. Instead of a signature,
        this transaction includes a random string of 48 bytes (so that every two creation transactions are different).
        This function is a secret function that only the bank can use (currently for tests, and will make sense in a later exercise).
        """
        signature = Signature(secrets.token_bytes(48))
        transaction = Transaction(target, None, signature)
        self.mem_pool.append(transaction)
