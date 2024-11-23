from .utils import BlockHash
from .transaction import Transaction
from typing import List


class Block:
    # implement __init__ as you see fit.

    def get_block_hash(self) -> BlockHash:
        """returns hash of this block"""
        raise NotImplementedError()

    def get_transactions(self) -> List[Transaction]:
        """returns the list of transactions in this block."""
        raise NotImplementedError()

    def get_prev_block_hash(self) -> BlockHash:
        """Gets the hash of the previous block in the chain"""
        raise NotImplementedError()
