from .utils import BlockHash
from .transaction import Transaction
from typing import List
import hashlib


class Block:
    def __init__(self, transactions: List[Transaction], prev_block_hash: BlockHash):
        """
        Initializes a block with a list of transactions and the hash of the previous block.

        :param transactions: List of transactions included in this block.
        :param prev_block_hash: The hash of the previous block in the chain.
        """
        self.transactions = transactions
        self.prev_block_hash = prev_block_hash

    def get_block_hash(self) -> BlockHash:
        """
        Calculates and returns the hash of this block.
        The hash is computed using:
        - The hash of the previous block.
        - The concatenated, serialized representations of all transactions in the block.
        """
        # Serialize all transactions
        serialized_transactions = b"".join(tx.get_txid() for tx in self.transactions)

        # Combine the serialized transactions with the previous block's hash
        block_content = self.prev_block_hash + serialized_transactions

        # Compute the block hash using SHA256
        block_hash = hashlib.sha256(block_content).digest()
        return BlockHash(block_hash)

    def get_transactions(self) -> List[Transaction]:
        """
        Returns the list of transactions included in this block.
        """
        return self.transactions

    def get_prev_block_hash(self) -> BlockHash:
        """
        Returns the hash of the previous block.
        """
        return self.prev_block_hash
