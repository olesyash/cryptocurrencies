import hashlib
import os

from .utils import *
from .block import Block
from .transaction import Transaction
from typing import Set, Optional, List


class Node:
    def __init__(self) -> None:
        """Creates a new node with an empty mempool and no connections to others.
        Blocks mined by this node will reward the miner with a single new coin,
        created out of thin air and associated with the mining reward address"""
        self.mem_pool: List[Transaction] = []
        self.private_key, self.public_key = gen_keys()
        self.connections = Set['Node']()
        self.blockchain: List[Block] = []
        self.utxos: List[Transaction] = []
        self.latest_block_hash: BlockHash = BlockHash(b"Genesis")

    def connect(self, other: 'Node') -> None:
        """connects this node to another node for block and transaction updates.
        Connections are bi-directional, so the other node is connected to this one as well.
        Raises an exception if asked to connect to itself.
        The connection itself does not trigger updates about the mempool,
        but nodes instantly notify of their latest block to each other (see notify_of_block)"""
        # Check if attempting to connect to self
        if self is other:
            raise ValueError("A node cannot connect to itself")

        # Add bidirectional connections
        self.connections.add(other)
        other.connections.add(self)

        # Notify each other of the latest block
        self.notify_of_block(self.latest_block_hash, other)
        other.notify_of_block(other.latest_block_hash, self)

    def disconnect_from(self, other: 'Node') -> None:
        """Disconnects this node from the other node. If the two were not connected, then nothing happens"""
        # Check if the other node is in this node's connections
        if other in self.connections:
            # Remove the connection in both directions
            self.connections.remove(other)
            other.connections.remove(self)

    def get_connections(self) -> Set['Node']:
        """Returns a set containing the connections of this node."""
        return self.connections

    def add_transaction_to_mempool(self, transaction: Transaction) -> bool:
        """
        This function inserts the given transaction to the mempool.
        It will return False iff any of the following conditions hold:
        (i) the transaction is invalid (the signature fails)
        (ii) the source doesn't have the coin that it tries to spend
        (iii) there is contradicting tx in the mempool.

        If the transaction is added successfully, then it is also sent to neighboring nodes.
        """
        # Check if the transaction is valid
        if not verify(transaction.get_txid(), transaction.signature, transaction.output):
            return False

        # Check if the source has the coin
        if transaction.input not in self.utxos:
            return False

        # Check for contradicting transactions in the mempool
        for tx in self.mem_pool:
            if tx.input == transaction.input:
                return False

        # Add the transaction to the mempool
        self.mem_pool.append(transaction)

        # Send the transaction to neighboring nodes
        for node in self.connections:
            node.add_transaction_to_mempool(transaction)

        return True

    def notify_of_block(self, block_hash: BlockHash, sender: 'Node') -> None:
        """
        This method is used by a node's connection to inform it that it has learned of a
        new block (or created a new block). If the block is unknown to the current Node, The block is requested.
        We assume the sender of the message is specified, so that the node can choose to request this block if
        it wishes to do so.
        (if it is part of a longer unknown chain, these blocks are requested as well, until reaching a known block).
        Upon receiving new blocks, they are processed and checked for validity (check all signatures, hashes,
        block size , etc.).
        If the block is on the longest chain, the mempool and utxo change accordingly.
        If the block is indeed the tip of the longest chain,
        a notification of this block is sent to the neighboring nodes of this node.
        (no need to notify of previous blocks -- the nodes will fetch them if needed)
        """
        if block_hash not in [block.get_block_hash() for block in self.blockchain]:
            # Request the block from the sender
            block = sender.get_block(block_hash)
            self.blockchain.append(block)
            # Process and validate the block
            # (Assuming a validate_block function exists)
            if self.validate_block(block):
                # Update mempool and utxo
                self.update_mempool_and_utxo(block)
                # Notify neighboring nodes
                for node in self.connections:
                    node.notify_of_block(block_hash, self)

    @staticmethod
    def validate_block(block: Block) -> bool:
        """
        Validates the given block by checking all signatures, hashes, and block size.
        Returns True if the block is valid, otherwise False.
        """
        # Check block size
        if len(block.get_transactions()) > BLOCK_SIZE:
            return False

        # Validate each transaction in the block
        for tx in block.get_transactions():
            if not verify(tx.get_txid(), tx.signature, tx.output):
                return False

        # Validate block hash
        block_data = b''.join(tx.get_txid() for tx in block.get_transactions())
        if block.get_block_hash() != hashlib.sha256(block_data).digest():
            return False

        return True

    def update_mempool_and_utxo(self, block: Block) -> None:
        """
        Updates the mempool and UTXO set based on the transactions in the given block.
        """
        for tx in block.get_transactions():
            # Remove the transaction from the mempool if it exists
            self.mem_pool = [mempool_tx for mempool_tx in self.mem_pool if mempool_tx.get_txid() != tx.get_txid()]

            # Update UTXO set
            if tx.input:
                self.utxos = [utxo for utxo in self.utxos if utxo.get_txid() != tx.input]
            self.utxos.append(tx)

    def mine_block(self) -> Optional[BlockHash]:
        """
        This function allows the node to create a single block.
        The block should contain BLOCK_SIZE transactions (unless there aren't enough in the mempool). Of these,
        BLOCK_SIZE-1 transactions come from the mempool and one additional transaction will be included that creates
        money and adds it to the address of this miner.
        Money creation transactions have None as their input, and instead of a signature, contain 48 random bytes.
        If a new block is created, all connections of this node are notified by calling their notify_of_block() method.
        The method returns the new block hash (or None if there was no block)
        """
        if len(self.mem_pool) < BLOCK_SIZE - 1:
            return None

        # Create a coinbase transaction
        coinbase_tx = Transaction(self.public_key, None, Signature(os.urandom(48)))

        # Select transactions from the mempool
        transactions = self.mem_pool[:BLOCK_SIZE - 1]
        transactions.append(coinbase_tx)

        # Create a new block
        new_block = Block(transactions, self.get_latest_hash())
        self.blockchain.append(new_block)

        # Notify connections
        for node in self.connections:
            node.notify_of_block(new_block.get_block_hash(), self)

        return new_block.get_block_hash()

    def get_block(self, block_hash: BlockHash) -> Block:
        """
        This function returns a block object given its hash.
        If the block doesn't exist, a ValueError is raised.
        """
        for block in self.blockchain:
            if block.get_block_hash() == block_hash:
                return block
        raise ValueError(f"Block with hash {block_hash} not found")

    def get_latest_hash(self) -> BlockHash:
        """
        This function returns the last block hash known to this node (the tip of its current chain).
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
        return self.utxos

    # ------------ Formerly wallet methods: -----------------------

    def create_transaction(self, target: PublicKey) -> Optional[Transaction]:
        """
        This function returns a signed transaction that moves an unspent coin to the target.
        It chooses the coin based on the unspent coins that this node has.
        If the node already tried to spend a specific coin, and such a transaction exists in its mempool,
        but it did not yet get into the blockchain then it shouldn't try to spend it again (until clear_mempool() is
        called -- which will wipe the mempool and thus allow to attempt these re-spends).
        The method returns None if there are no outputs that have not been spent already.

        The transaction is added to the mempool (and as a result is also published to neighboring nodes)
        """
        for utxo in self.utxos:
            if utxo not in [tx.input for tx in self.mem_pool]:
                message = utxo.get_txid() + target
                signature = sign(message, self.private_key)
                new_tx = Transaction(target, utxo.get_txid(), signature)
                if self.add_transaction_to_mempool(new_tx):
                    return new_tx
        return None

    def clear_mempool(self) -> None:
        """
        Clears the mempool of this node. All transactions waiting to be entered into the next block are gone.
        """
        self.mem_pool.clear()

    def get_balance(self) -> int:
        """
        This function returns the number of coins that this node owns according to its view of the blockchain.
        Coins that the node owned and sent away will still be considered as part of the balance until the spending
        transaction is in the blockchain.
        """
        return len(self.utxos)

    def get_address(self) -> PublicKey:
        """
        This function returns the public address of this node (its public key).
        """
        return self.public_key


"""
Importing this file should NOT execute code. It should only create definitions for the objects above.
Write any tests you have in a different file.
You may add additional methods, classes and files but be sure no to change the signatures of methods
included in this template.
"""
