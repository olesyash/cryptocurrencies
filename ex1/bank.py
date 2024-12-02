import secrets
from .utils import BlockHash, PublicKey
from .transaction import Transaction
from .block import Block
from typing import List, Set
from .utils import *


class Bank:
    def __init__(self) -> None:
        """Creates a bank with an empty blockchain and an empty mempool."""
        self.mem_pool: List[Transaction] = []
        self.blockchain: List[Block] = []
        self.latest_block_hash: BlockHash = BlockHash(b"Genesis")

    def add_transaction_to_mempool(self, transaction: Transaction) -> bool:
        """
        This function inserts the given transaction to the mempool.
        It will return False if one of the following conditions hold:
        (i) the transaction is invalid (the signature fails)
        (ii) the source doesn't have the coin that he tries to spend
        (iii) there is contradicting tx in the mempool.
        (iv) there is no input (i.e., this is an attempt to create money from nothing)
        """
        if not transaction:
            return False

        new_tx = Transaction(transaction.output, transaction.input, transaction.signature)
        new_tx_id = new_tx.get_txid()
        if new_tx_id != transaction.get_txid():
            return False

        # Check if the transaction has a valid input and signature
        input_tx = next((tx for tx in self.get_utxo() if tx.get_txid() == transaction.input), None)

        if not input_tx or not self.verify_transaction(transaction, input_tx):
            return False

        # Ensure no contradicting transactions in the mempool
        if any(tx.input == transaction.input for tx in self.mem_pool):
            return False

        # Check if the transaction is attempting to create money improperly
        if transaction.input is None:
            return False

        # Check if the transaction is already in the mempool
        if transaction in self.mem_pool:
            return False

        # Add the transaction to the mempool
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
        if not self.blockchain:
            return self.latest_block_hash
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
        spent_outputs = set()  # Set of (transaction_hash, output_index)
        # Collect unspent transactions
        utxo: List[Transaction] = []

        # First, collect all spent outputs from confirmed transactions in all blocks
        for block in self.blockchain:
            for transaction in block.get_transactions():
                if transaction.input is not None:
                    print(f"Spent output: {transaction.input}")
                    # If a transaction has an input, it means it spent a previous coin
                    spent_outputs.add(transaction.input)

        # Iterate through blocks in reverse order (newest first)
        seen_outputs = set()
        for block in reversed(self.blockchain):
            # For each block, check its transactions
            for transaction in block.get_transactions():
                print(f"Checking transaction: {transaction}, Input: {transaction.input}, Output: {transaction.output}")
                # If this output hasn't been spent, mark the transaction as having unspent outputs
                if transaction.output not in seen_outputs:
                    if transaction.input is None or transaction.get_txid() not in spent_outputs:
                        # If the transaction has any unspent outputs, add it to the UTXO list
                        print(f"Adding to UTXO: {transaction}")
                        utxo.append(transaction)
                        seen_outputs.add(transaction.output)
        return utxo

    def create_money(self, target: PublicKey) -> None:
        """
        This function inserts a transaction into the mempool that creates a single coin out of thin air. Instead of a signature,
        this transaction includes a random string of 48 bytes (so that every two creation transactions are different).
        This function is a secret function that only the bank can use (currently for tests, and will make sense in a later exercise).
        """
        signature = Signature(secrets.token_bytes(48))
        transaction = Transaction(target, None, signature)
        self.mem_pool.append(transaction)

    def verify_transaction(self, transaction: Transaction, input_tx: Transaction) -> bool:
        """
        Verifies that a transaction is valid by checking its signature against the input transaction's output.
        """
        # Ensure the input transaction's output matches the transaction's public key
        if transaction.input != input_tx.get_txid():
            return False

        # Verify the signature against the public key
        return verify(
            message=input_tx.get_txid() + transaction.output,
            sig=transaction.signature,
            pub_key=input_tx.output,
        )
