import hashlib
import os
import secrets
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
        self.connections : Set['Node'] = set() 
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

        # Add bidirectional connections if not already connected
        if other not in self.connections:
            self.connections.add(other)
            if self not in other.connections:
                other.connections.add(self)

            # Notify of latest blocks - let the node with more blocks notify first
            if len(self.blockchain) >= len(other.blockchain):
                if self.latest_block_hash != GENESIS_BLOCK_PREV:
                    other.notify_of_block(self.latest_block_hash, self)
            else:
                if other.latest_block_hash != GENESIS_BLOCK_PREV:
                    self.notify_of_block(other.latest_block_hash, other)

    def disconnect_from(self, other: 'Node') -> None:
        """Disconnects this node from the other node. If the two were not connected, then nothing happens"""
        if other in self.connections:
            self.connections.discard(other)
            if self in other.connections:
                other.connections.discard(self)

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
        (iv) it's a coinbase transaction (those can only be created through mining)

        If the transaction is added successfully, then it is also sent to neighboring nodes.
        """
        # Skip if transaction is already in mempool
        if transaction in self.mem_pool:
            return True

        # Reject coinbase transactions - they can only be created through mining
        if transaction.input is None:
            return False

        # Find the UTXO being spent
        utxo = None
        for u in self.utxos:
            if u.get_txid() == transaction.input:
                utxo = u
                break

        # Check if the source has the coin
        if utxo is None:
            return False

        # Check if the transaction is valid (signature matches)
        message = transaction.input + transaction.output
        if not verify(message, transaction.signature, utxo.output):
            return False

        # Check for contradicting transactions in the mempool
        for tx in self.mem_pool:
            if tx.input == transaction.input:
                return False

        # Add the transaction to the mempool
        self.mem_pool.append(transaction)

        # Send the transaction to neighboring nodes
        for node in self.connections:
            if transaction not in node.get_mempool():  # Only forward if node doesn't have it
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
        # If we already have this block, nothing to do
        if block_hash in [block.get_block_hash() for block in self.blockchain]:
            return

        # First verify that this chain leads to Genesis
        current_hash = block_hash
        blocks_to_add = []
        try:
            while current_hash != GENESIS_BLOCK_PREV and current_hash not in [block.get_block_hash() for block in self.blockchain]:
                current_block = sender.get_block(current_hash)
                # Verify that the block matches the hash we requested
                if current_block.get_block_hash() != current_hash:
                    return
                blocks_to_add.insert(0, current_block)  # Add to front to maintain order
                current_hash = current_block.get_prev_block_hash()
        except ValueError:
            # Chain doesn't lead to Genesis or a known block
            return

        # Find where the chains diverge
        fork_point = -1
        if current_hash != GENESIS_BLOCK_PREV:
            fork_point = next((i for i, block in enumerate(self.blockchain) 
                             if block.get_block_hash() == current_hash), -1)

        # Compare chain lengths from fork point
        current_chain_length = len(self.blockchain) - (fork_point + 1)
        new_chain_length = len(blocks_to_add)

        # Only switch if new chain is longer
        if new_chain_length > current_chain_length:
            # Save current mempool
            old_mempool = self.mem_pool.copy()

            # Reset state to fork point
            self.blockchain = self.blockchain[:fork_point + 1] if fork_point >= 0 else []
            self.utxos = []
            self.mem_pool = []

            # Rebuild UTXOs from fork point
            for block in self.blockchain:
                self.update_mempool_and_utxo(block)

            # Add new blocks one by one, stopping at first invalid block
            for block in blocks_to_add:
                if not self.validate_block(block):
                    # Stop processing blocks but keep what we've validated so far
                    break
                self.blockchain.append(block)
                self.update_mempool_and_utxo(block)
                self.latest_block_hash = block.get_block_hash()

                # Notify neighbors of the valid block
                for node in self.connections:
                    if node != sender:  # Don't notify the sender
                        node.notify_of_block(block.get_block_hash(), self)

            # If we didn't process any blocks, restore genesis state
            if not self.blockchain:
                self.latest_block_hash = GENESIS_BLOCK_PREV

            # Restore mempool transactions that weren't included in the new chain
            all_txids = {tx.get_txid() for block in self.blockchain[fork_point + 1:] for tx in block.get_transactions()}
            for tx in old_mempool:
                if tx.get_txid() not in all_txids and self.validate_transaction(tx):
                    self.mem_pool.append(tx)

    def validate_block(self, block: Block) -> bool:
        """
        Validates the given block by checking all signatures, hashes, and block size.
        Returns True if the block is valid, otherwise False.
        """
        # Check block size
        if len(block.get_transactions()) > BLOCK_SIZE:
            return False

        # Only one coinbase transaction allowed per block
        coinbase_count = sum(1 for tx in block.get_transactions() if tx.input is None)
        if coinbase_count > 1:
            return False

        # Check for duplicate transactions within block
        txids = set()
        for tx in block.get_transactions():
            if tx.get_txid() in txids:
                return False
            txids.add(tx.get_txid())

        # Track spent transaction IDs within this block
        spent_txids = set()

        # Validate each transaction in the block
        for tx in block.get_transactions():
            # Skip signature validation for coinbase transactions
            if tx.input is None:
                continue

            # Check for double spending within block
            if tx.input in spent_txids:
                return False
            spent_txids.add(tx.input)

            # For regular transactions, find the UTXO being spent
            utxo = None
            for prev_block in self.blockchain:
                for prev_tx in prev_block.get_transactions():
                    if prev_tx.get_txid() == tx.input:
                        utxo = prev_tx
                        break
                if utxo:
                    break

            # Check if we found the UTXO
            if utxo is None:
                return False

            # Verify the signature
            message = tx.input + tx.output
            if not verify(message, tx.signature, utxo.output):
                return False

        return True

    def validate_transaction(self, transaction: Transaction) -> bool:
        """
        Validates a single transaction by checking its signature and ensuring the input exists in UTXOs.
        Returns True if the transaction is valid, otherwise False.
        """
        # Coinbase transactions are always valid
        if transaction.input is None:
            return True

        # Find the UTXO being spent
        utxo = None
        for tx in self.utxos:
            if tx.get_txid() == transaction.input:
                utxo = tx
                break

        # Check if UTXO exists and verify signature
        if utxo is None:
            return False

        message = transaction.input + transaction.output
        return verify(message, transaction.signature, utxo.output)

    def update_mempool_and_utxo(self, block: Block) -> None:
        """
        Updates the mempool and UTXO set based on the transactions in the given block.
        """
        # Remove spent transactions from UTXOs and add new ones
        for tx in block.get_transactions():
            # Remove spent UTXO
            if tx.input is not None:  # Skip coinbase transactions
                self.utxos = [utxo for utxo in self.utxos if utxo.get_txid() != tx.input]

            # Add new UTXO
            self.utxos.append(tx)

        # Remove transactions from mempool that are now in the block
        block_txids = {tx.get_txid() for tx in block.get_transactions()}
        self.mem_pool = [tx for tx in self.mem_pool if tx.get_txid() not in block_txids]

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
        # Create coinbase transaction
        coinbase_tx = Transaction(self.public_key, None, Signature(secrets.token_bytes(64)))

        # Get transactions from mempool (up to BLOCK_SIZE-1)
        block_txs = [coinbase_tx]
        if len(self.mem_pool) > 0:
            block_txs.extend(self.mem_pool[:BLOCK_SIZE - 1])

        # Create and add the block
        block = Block(self.latest_block_hash, block_txs)
        self.blockchain.append(block)
        self.update_mempool_and_utxo(block)
        self.latest_block_hash = block.get_block_hash()

        # Notify neighbors
        for node in self.connections:
            node.notify_of_block(block.get_block_hash(), self)

        return block.get_block_hash()

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
        return self.latest_block_hash

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
        The transaction is added to the mempool (and as a result is also published to neighboring nodes)
        """
        # Validate target address
        if target is None:
            return None

        # Find an unspent transaction that we own and haven't tried to spend yet
        for utxo in self.utxos:
            # Skip if we've already tried to spend this UTXO
            if any(tx.input == utxo.get_txid() for tx in self.mem_pool):
                continue

            # Check if we own this UTXO
            if utxo.output == self.public_key:
                # Create and sign the transaction
                txid = utxo.get_txid()
                message = txid + target
                signature = sign(message, self.private_key)
                new_tx = Transaction(target, txid, signature)
                if self.add_transaction_to_mempool(new_tx):
                    return new_tx

        return None

    def clear_mempool(self) -> None:
        """
        Clears the mempool of this node. All transactions waiting to be entered into the next block are gone.
        """
        self.mem_pool = []

    def get_balance(self) -> int:
        """
        This function returns the number of coins that this node owns according to its view of the blockchain.
        Coins that the node owned and sent away will still be considered as part of the balance until the spending
        transaction is in the blockchain.
        """
        balance = 0
        for utxo in self.utxos:
            if utxo.output == self.public_key:
                balance += 1
        return balance

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
