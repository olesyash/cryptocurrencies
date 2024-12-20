from ex2 import *
import pytest
import secrets
import hashlib
from typing import Callable, List, Any
from unittest.mock import Mock

EvilNodeMaker = Callable[[List[Block]], Mock]
KeyFactory = Callable[[], PublicKey]


def test_wallet_functionality_at_init(alice: Node) -> None:
    assert alice.get_address()
    assert alice.get_balance() == 0
    assert alice.create_transaction(alice.get_address()) is None


def test_node_functionality_at_init(alice: Node) -> None:
    assert alice.get_utxo() == []
    assert alice.get_latest_hash() == GENESIS_BLOCK_PREV
    assert alice.get_mempool() == []


def test_mine_single_block_and_generate_coin(alice: Node) -> None:
    block_hash = alice.mine_block()
    assert block_hash != GENESIS_BLOCK_PREV
    assert alice.get_latest_hash() == block_hash
    assert len(alice.get_utxo()) == 1
    assert alice.get_mempool() == []
    assert alice.get_balance() == 1

    block = alice.get_block(block_hash)
    assert block.get_block_hash() == block_hash
    assert block.get_prev_block_hash() == GENESIS_BLOCK_PREV
    transactions = block.get_transactions()
    assert transactions[0] == alice.get_utxo()[0]
    assert transactions[0].input is None
    assert transactions[0].output == alice.get_address()


def test_retreive_block_fails_on_junk_hash(alice: Node) -> None:
    with pytest.raises(ValueError):
        alice.get_block(GENESIS_BLOCK_PREV)
    bogus_hash = BlockHash(hashlib.sha256(b"no_such_block").digest())
    with pytest.raises(ValueError):
        alice.get_block(bogus_hash)
    h = alice.mine_block()
    with pytest.raises(ValueError):
        alice.get_block(bogus_hash)
    assert alice.get_block(h)


def test_transaction_creation(alice: Node, bob: Node, charlie: Node) -> None:
    alice.mine_block()
    assert alice.get_balance() == 1
    tx = alice.create_transaction(bob.get_address())
    assert tx is not None
    assert tx.input == alice.get_utxo()[0].get_txid()
    assert tx.output == bob.get_address()
    assert bob.get_balance() == 0
    assert charlie.get_balance() == 0


def test_node_updates_when_notified(alice: Node, evil_node_maker: EvilNodeMaker) -> None:
    block1 = Block(GENESIS_BLOCK_PREV, [Transaction(
        gen_keys()[1], None, Signature(secrets.token_bytes(64)))])
    block_chain = [block1]
    eve = evil_node_maker(block_chain)
    alice.notify_of_block(eve.get_latest_hash(), eve)
    assert alice.get_latest_hash() != GENESIS_BLOCK_PREV


def test_node_updates_when_notified_two_blocks(alice: Node, evil_node_maker: EvilNodeMaker) -> None:
    tx1 = Transaction(gen_keys()[1], None, Signature(secrets.token_bytes(64)))
    block1 = Block(GENESIS_BLOCK_PREV, [tx1])
    tx2 = Transaction(gen_keys()[1], None, Signature(secrets.token_bytes(64)))
    block2 = Block(block1.get_block_hash(), [tx2])

    block_chain = [block1, block2]
    eve = evil_node_maker(block_chain)
    alice.notify_of_block(eve.get_latest_hash(), eve)
    assert alice.get_latest_hash() == block2.get_block_hash()
    assert tx1 in alice.get_utxo()
    assert tx2 in alice.get_utxo()
    assert len(alice.get_utxo()) == 2
    assert alice.get_block(block1.get_block_hash()) == block1
    assert alice.get_block(block2.get_block_hash()) == block2


def test_node_does_not_update_when_alternate_chain_does_not_lead_to_genesis(alice: Node, evil_node_maker: EvilNodeMaker) -> None:
    block1 = Block(BlockHash(hashlib.sha256(b"Not Genesis").digest()),
                   [Transaction(gen_keys()[1], None, Signature(secrets.token_bytes(64)))])
    block2 = Block(block1.get_block_hash(), [Transaction(
        gen_keys()[1], None, Signature(secrets.token_bytes(64)))])
    block3 = Block(block2.get_block_hash(), [Transaction(
        gen_keys()[1], None, Signature(secrets.token_bytes(64)))])

    evil_node = evil_node_maker([block1, block2, block3])

    alice.notify_of_block(block3.get_block_hash(), evil_node)


def test_node_does_not_fully_update_when_some_transaction_is_bad(alice: Node, bob: Node, evil_node_maker: EvilNodeMaker) -> None:
    bob.mine_block()
    tx0 = bob.create_transaction(alice.get_address())
    assert tx0 is not None
    tx1 = Transaction(gen_keys()[1], None, Signature(secrets.token_bytes(64)))
    block1 = Block(GENESIS_BLOCK_PREV, [tx1])

    tx2 = Transaction(gen_keys()[1], None, Signature(secrets.token_bytes(64)))

    tx3 = Transaction(gen_keys()[1], tx1.get_txid(),
                      tx0.signature)  # the sig here is wrong!

    block2 = Block(block1.get_block_hash(), [tx2, tx3])
    mock_node = evil_node_maker([block1, block2])
    alice.notify_of_block(mock_node.get_latest_hash(), mock_node)
    assert alice.get_latest_hash() == block1.get_block_hash()


def test_node_does_not_update_when_creating_too_much_money(alice: Node, evil_node_maker: EvilNodeMaker) -> None:
    tx1 = Transaction(gen_keys()[1], None, Signature(secrets.token_bytes(64)))
    tx2 = Transaction(gen_keys()[1], None, Signature(secrets.token_bytes(64)))
    block = Block(GENESIS_BLOCK_PREV, [tx1, tx2])
    mock_node = evil_node_maker([block])
    alice.notify_of_block(mock_node.get_latest_hash(), mock_node)
    assert alice.get_latest_hash() == GENESIS_BLOCK_PREV
    assert alice.get_utxo() == []


def test_node_double_spends_when_mempool_clears(alice: Node, bob: Node) -> None:
    alice.mine_block()
    tx1 = alice.create_transaction(bob.get_address())
    assert tx1 is not None
    tx2 = alice.create_transaction(bob.get_address())
    assert tx2 is None
    alice.clear_mempool()
    assert alice.get_mempool() == []
    tx3 = alice.create_transaction(bob.get_address())
    assert tx3 is not None


def test_transactions_to_different_targets_are_different(alice: Node, bob: Node, charlie: Node) -> None:
    alice.mine_block()
    tx1 = alice.create_transaction(bob.get_address())
    alice.clear_mempool()
    tx2 = alice.create_transaction(charlie.get_address())
    assert tx1 is not None and tx2 is not None
    assert tx1.get_txid() != tx2.get_txid()


def test_transaction_rejected_if_we_change_output(alice: Node, bob: Node, charlie: Node) -> None:
    alice.mine_block()
    tx = alice.create_transaction(bob.get_address())
    assert tx is not None
    tx2 = Transaction(charlie.get_address(), tx.input, tx.signature)
    alice.clear_mempool()
    assert alice.add_transaction_to_mempool(tx)
    alice.clear_mempool()
    assert not alice.add_transaction_to_mempool(tx2)


def test_transaction_not_propagated_if_it_double_spends_a_mempool_tx(alice: Node, bob: Node, charlie: Node) -> None:
    alice.connect(bob)
    alice.mine_block()
    tx1 = alice.create_transaction(bob.get_address())
    assert tx1 is not None
    alice.clear_mempool()
    assert tx1 in bob.get_mempool()
    bob.connect(charlie)
    tx2 = alice.create_transaction(charlie.get_address())
    assert tx2 is not None
    assert tx2 in alice.get_mempool()
    assert tx2 not in bob.get_mempool()
    assert tx2 not in charlie.get_mempool()


def test_connections_exist(alice: Node, bob: Node, charlie: Node) -> None:
    assert alice.get_connections() == set()
    alice.connect(bob)
    assert bob in alice.get_connections()
    assert alice in bob.get_connections()

    bob.connect(charlie)
    bob.disconnect_from(alice)
    assert bob not in alice.get_connections()
    assert alice not in bob.get_connections()
    assert charlie in bob.get_connections()


def test_connect_to_self_fails(alice: Node) -> None:
    with pytest.raises(Exception):
        alice.connect(alice)


def test_connections_propagate_blocks(alice: Node, bob: Node, charlie: Node) -> None:
    alice.connect(bob)
    alice.mine_block()
    assert len(bob.get_utxo()) == 1
    assert alice.get_latest_hash() == bob.get_latest_hash()
    assert charlie.get_latest_hash() == GENESIS_BLOCK_PREV


def test_connections_propagate_txs(alice: Node, bob: Node, charlie: Node) -> None:
    alice.connect(bob)
    alice.mine_block()

    tx = alice.create_transaction(bob.get_address())
    assert tx in bob.get_mempool()
    assert tx not in charlie.get_mempool()


def test_block_hash(alice: Node) -> None:
    block_hash1 = alice.mine_block()
    block1 = alice.get_block(block_hash1)
    assert block1.get_block_hash() == block_hash1

    transactions = block1.get_transactions()
    prev = block1.get_prev_block_hash()
    bogus_hash = BlockHash(hashlib.sha256(b"no_such_block").digest())
    block2 = Block(bogus_hash, transactions)
    block3 = Block(prev, transactions * 2)
    block4 = Block(prev, [])
    assert block2.get_block_hash() != block_hash1
    assert block3.get_block_hash() != block_hash1
    assert block4.get_block_hash() != block_hash1


def test_catching_up_after_disconnect(alice: Node, bob: Node) -> None:
    alice.connect(bob)
    alice.mine_block()
    alice.disconnect_from(bob)
    h2 = alice.mine_block()
    alice.connect(bob)
    assert bob.get_latest_hash() == h2


def test_longer_chain_overtake(alice: Node, bob: Node) -> None:
    h1 = alice.mine_block()
    h2 = alice.mine_block()
    bob.mine_block()
    alice.connect(bob)
    assert bob.get_latest_hash() == h2
    assert bob.get_block(h2).get_prev_block_hash() == h1
    assert bob.get_block(h1).get_prev_block_hash() == GENESIS_BLOCK_PREV
    assert set(bob.get_utxo()) == set(alice.get_utxo())


def test_tx_surives_in_mempool_if_not_included_in_block(alice: Node, bob: Node) -> None:
    alice.connect(bob)
    bob.mine_block()
    bob.create_transaction(alice.get_address())
    bob.disconnect_from(alice)

    alice.clear_mempool()
    block_hash = alice.mine_block()
    bob.connect(alice)
    assert bob.get_latest_hash() == block_hash
    assert len(bob.get_mempool()) == 1


def test_tx_replaced_in_blockchain_when_double_spent(alice: Node, bob: Node, charlie: Node) -> None:
    alice.connect(bob)
    alice.connect(charlie)
    alice.mine_block()
    alice.disconnect_from(charlie)
    tx1 = alice.create_transaction(bob.get_address())
    alice.mine_block()
    alice.disconnect_from(bob)

    assert tx1 in bob.get_utxo()
    assert tx1 in alice.get_utxo()

    charlie.mine_block()
    charlie.mine_block()

    alice.connect(charlie)
    alice.clear_mempool()  # in case you restore transactions to mempool
    assert tx1 not in alice.get_utxo()
    assert tx1 not in alice.get_mempool()
    tx2 = alice.create_transaction(charlie.get_address())
    assert tx2 is not None
    assert tx2 in alice.get_mempool()
    alice.mine_block()
    alice.mine_block()
    assert tx2 in alice.get_utxo()
    alice.connect(bob)
    assert tx2 in bob.get_utxo()
    assert tx1 not in bob.get_utxo()
    assert tx1 not in bob.get_mempool()


def test_bob_serves_wrong_block(alice: Node, bob: Node, charlie: Node, monkeypatch: Any) -> None:
    # we ask charlie to create a block
    h1 = charlie.mine_block()
    block = charlie.get_block(h1)

    h2 = bob.mine_block()

    # now we make bob respond to block requests with charlie's block
    monkeypatch.setattr(bob, "get_block", lambda block_hash: block)

    alice.connect(bob)
    assert alice.get_latest_hash() == GENESIS_BLOCK_PREV
    assert alice.get_utxo() == []

##################################################

def test_block_with_invalid_previous_hash(alice: Node, bob: Node) -> None:
    # Create a block with an invalid previous hash
    invalid_prev_hash = BlockHash(hashlib.sha256(b"Invalid Hash").digest())
    tx = Transaction(alice.get_address(), None, Signature(secrets.token_bytes(64)))
    block = Block(invalid_prev_hash, [tx])

    # Notify Alice of the invalid block
    alice.connect(bob)
    bob.mine_block()
    assert alice.get_latest_hash() != GENESIS_BLOCK_PREV
    alice.notify_of_block(block.get_block_hash(), bob)
    assert alice.get_latest_hash() == bob.get_latest_hash()


def test_transaction_with_invalid_signature(alice: Node, bob: Node) -> None:
    alice.mine_block()
    invalid_sig = Signature(secrets.token_bytes(64))  # Random signature
    invalid_tx = Transaction(bob.get_address(), alice.get_utxo()[0].get_txid(), invalid_sig)

    # Attempt to add invalid transaction to mempool
    assert not alice.add_transaction_to_mempool(invalid_tx)


def test_block_includes_duplicate_transactions(alice: Node, bob: Node, evil_node_maker: EvilNodeMaker) -> None:
    alice.mine_block()
    bob.connect(alice)
    tx1 = alice.create_transaction(alice.get_address())
    bob.mine_block()
    tx2 = bob.create_transaction(alice.get_address())

    # alice.connect(bob)
    block1 = Block(GENESIS_BLOCK_PREV, [tx1])  # Duplicate transactions
    block2 = Block(block1.get_block_hash(), [tx2, tx2])  # Duplicate transactions
    block3 = Block(block2.get_block_hash(), [Transaction(gen_keys()[1], None, Signature(secrets.token_bytes(64)))])
    block_chain = [block1, block2,block3]
    eve = evil_node_maker(block_chain)
    # Notify Alice of a block with duplicate transactions
    alice.notify_of_block(block3.get_block_hash(), eve)
    assert alice.get_latest_hash() != block3.get_block_hash()


def test_invalid_block_hash_provided_in_chain(alice: Node, bob: Node) -> None:
    alice.mine_block()
    bob.mine_block()
    fake_hash = BlockHash(hashlib.sha256(b"Fake Block").digest())
    with pytest.raises(ValueError):
        alice.get_block(fake_hash)


def test_unspent_output_double_spent_in_block(alice: Node, bob: Node) -> None:
    alice.mine_block()
    tx1 = alice.create_transaction(bob.get_address())
    # tx1 = Transaction(alice.get_address(), None, Signature(secrets.token_bytes(64)))

    # Create a block with the same transaction spent twice
    block = Block(
        GENESIS_BLOCK_PREV,
        [tx1, tx1],  # Double-spend
    )
    mock_node = Mock()
    mock_node.get_latest_hash.return_value = block.get_block_hash()
    mock_node.get_block.return_value = block

    bob.notify_of_block(block.get_block_hash(), mock_node)
    assert alice.get_balance() == 1


def test_inconsistent_chain_height(alice: Node, bob: Node) -> None:
    alice.mine_block()
    alice.mine_block()
    bob.mine_block()

    # Manually alter the chain height for Bob
    def fake_height():
        return 1  # Incorrect height
    bob.get_chain_height = fake_height

    alice.connect(bob)
    assert alice.get_latest_hash() == bob.get_latest_hash()


def test_propagating_invalid_transaction(alice: Node, bob: Node, charlie: Node) -> None:
    alice.connect(bob)
    bob.connect(charlie)
    alice.mine_block()

    # Create and propagate an invalid transaction
    invalid_tx = Transaction(bob.get_address(), None, Signature(secrets.token_bytes(64)))
    assert not alice.add_transaction_to_mempool(invalid_tx)
    assert invalid_tx not in bob.get_mempool()
    assert invalid_tx not in charlie.get_mempool()


def test_blockchain_loop_detection(alice: Node, bob: Node, evil_node_maker: EvilNodeMaker) -> None:
    # צור מפתח ציבורי פיקטיבי עבור עסקאות
    public_key, _ = gen_keys()

    # צור את הבלוק הראשון
    tx1 = Transaction(public_key, None, Signature(secrets.token_bytes(64)))
    block1 = Block(GENESIS_BLOCK_PREV, [tx1])  # מצביע על block2 (לולאה)

    # צור את הבלוק השני
    tx2 = Transaction(public_key, None, Signature(secrets.token_bytes(64)))
    block2 = Block(block1.get_block_hash(), [tx2])  # מצביע על block1

    # עדכן את הבלוק הראשון שיצביע על block2
    block1.prev_block_hash = block2.get_block_hash()

    blockchain = [block1, block2]
    bob.blockchain = blockchain
    # נסה להוסיף את הבלוק הראשון (עם לולאה)
    alice.notify_of_block(block2.get_block_hash(), bob)
    assert alice.get_latest_hash() == GENESIS_BLOCK_PREV
    assert alice.get_utxo() == []

    block1.prev_block_hash = GENESIS_BLOCK_PREV
    alice.notify_of_block(block2.get_block_hash(), bob)


    # ודא שהמערכת לא מקבלת את הבלוק
    assert alice.get_latest_hash() == block2.get_block_hash()
    assert len(alice.get_utxo()) == 2

def test_append_two_different_blockchain(alice: Node, bob: Node, evil_node_maker: EvilNodeMaker) -> None:
    tx1 = Transaction(alice.get_address(), None, Signature(secrets.token_bytes(64)))
    tx2 = Transaction(alice.get_address(), None, Signature(secrets.token_bytes(64)))
    block1 = Block(hashlib.sha256(b"Invalid Genesis Hash").digest(), [tx1])
    block2 = Block(block1.get_block_hash(), [tx2])
    block_chain = [block1, block2]
    eve = evil_node_maker(block_chain)    
    alice.notify_of_block(block2.get_block_hash(), eve)
    assert alice.get_latest_hash() == GENESIS_BLOCK_PREV

def test_append_cut_blockchain(alice: Node, bob: Node, evil_node_maker: EvilNodeMaker) -> None:
    alice_block_hash = alice.mine_block()
    tx1 = Transaction(alice.get_address(), None, Signature(secrets.token_bytes(64)))
    tx2 = Transaction(alice.get_address(), None, Signature(secrets.token_bytes(64)))
    block1 = Block(alice.get_latest_hash(), [tx1])
    block2 = Block(block1.get_block_hash(), [tx2])
    block_chain = [block1, block2]
    eve = evil_node_maker(block_chain)    
    alice.notify_of_block(block1.get_block_hash(), eve)
    assert alice.get_latest_hash() == block1.get_block_hash()

def test_output_is_none(alice: Node, bob: Node, evil_node_maker: EvilNodeMaker) -> None:
    alice.mine_block()
    tx0 = alice.create_transaction(None)
    alice.add_transaction_to_mempool(tx0)
    alice.mine_block()

    tx1 = Transaction(bob.get_address(), alice.unspent_transaction[0].get_txid(), b"sig")
    tx2 = Transaction(bob.get_address(), alice.unspent_transaction[1].get_txid(), b"sig")
    assert alice.add_transaction_to_mempool(tx1) == False
    alice.add_transaction_to_mempool(tx2)
    assert alice.mine_block() is not None
    alice.connect(None)
    alice.disconnect_from(None)


def test_double_spend_tx(alice: Node, bob: Node, evil_node_maker: EvilNodeMaker) -> None:
    alice.mine_block()
    mined_tx = Transaction(alice.get_address(), None, Signature(secrets.token_bytes(64)))

    tx = alice.create_transaction(bob.get_address())
    block1 = Block(alice.get_latest_hash(),[mined_tx, tx ,tx])
    block2 = Block(block1.get_block_hash(),[mined_tx, tx])
    eve= evil_node_maker([block1, block2])
    alice.notify_of_block(block2.get_block_hash(), eve)
    assert alice.get_latest_hash() != block2.get_block_hash()

def test_overflow_size(alice: Node, bob: Node, evil_node_maker: EvilNodeMaker) -> None:
    for _ in range(12):
        alice.mine_block()
    txs = []
    for _ in range(12):
        txs.append(alice.create_transaction(bob.get_address()))

    mined_tx = Transaction(alice.get_address(), None, Signature(secrets.token_bytes(64)))
    block1 = Block(alice.get_latest_hash(),[mined_tx] + txs)
    eve = evil_node_maker([block1])
    alice.notify_of_block(block1.get_block_hash(), eve)
    assert alice.get_latest_hash() != block1.get_block_hash()

    alice.mine_block()
    assert len(alice.get_mempool()) == 3
    assert len(alice.get_block(alice.get_latest_hash()).get_transactions()) == BLOCK_SIZE
    assert alice.get_balance() == 4
    alice.clear_mempool()
    assert len(alice.get_mempool()) == 0
    assert alice.get_balance() == 4


    