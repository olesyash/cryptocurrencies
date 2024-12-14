from .utils import BlockHash
from .transaction import Transaction
from typing import List
import hashlib

class Block:
    def __init__(self, prev_block_hash: BlockHash, transactions: List[Transaction]):
        """
        Initializes a block with a list of transactions and the hash of the previous block.

        :param prev_block_hash: The hash of the previous block in the chain.
        :param transactions: List of transactions included in this block.
        """
        self.transactions = transactions
        self.prev_block_hash = prev_block_hash

    def get_block_hash(self) -> BlockHash:
        """Gets the hash of this block. 
        This function is used by the tests. Make sure to compute the result from the data in the block every time 
        and not to cache the result"""
        # Serialize all transactions
        serialized_transactions = b"".join(tx.get_txid() for tx in self.transactions)

        # Combine the serialized transactions with the previous block's hash
        block_content = self.prev_block_hash + serialized_transactions

        # Compute the block hash using SHA256
        block_hash = hashlib.sha256(block_content).digest()
        return BlockHash(block_hash)

    def get_transactions(self) -> List[Transaction]:
        """
        returns the list of transactions in this block.
        """
        return self.transactions

    def get_prev_block_hash(self) -> BlockHash:
        """Gets the hash of the previous block"""
        return self.prev_block_hash
