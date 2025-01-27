from ex1 import *


def test_block(bank: Bank, alice_coin: Transaction) -> None:
    hash1 = bank.get_latest_hash()
    block = bank.get_block(hash1)
    assert len(block.get_transactions()) == 1
    assert block.get_prev_block_hash() == GENESIS_BLOCK_PREV

    bank.end_day()

    hash2 = bank.get_latest_hash()
    block2 = bank.get_block(hash2)
    assert len(block2.get_transactions()) == 0
    assert block2.get_prev_block_hash() == hash1


def test_create_money_happy_flow(bank: Bank, alice: Wallet, bob: Wallet, alice_coin: Transaction) -> None:
    alice.update(bank)
    bob.update(bank)
    assert alice.get_balance() == 1
    assert bob.get_balance() == 0
    utxo = bank.get_utxo()
    assert len(utxo) == 1
    assert utxo[0].output == alice.get_address()


def test_transaction_happy_flow(bank: Bank, alice: Wallet, bob: Wallet,
                                alice_coin: Transaction) -> None:
    tx = alice.create_transaction(bob.get_address())
    assert tx is not None
    assert bank.add_transaction_to_mempool(tx)
    assert bank.get_mempool() == [tx]
    bank.end_day(limit=1)
    alice.update(bank)
    bob.update(bank)
    assert alice.get_balance() == 0
    assert bob.get_balance() == 1
    assert not bank.get_mempool()
    assert bank.get_utxo()[0].output == bob.get_address()
    assert tx == bank.get_block(bank.get_latest_hash()).get_transactions()[0]


def test_re_transmit_the_same_transaction(bank: Bank, alice: Wallet, bob: Wallet,
                                          alice_coin: Transaction) -> None:
    tx = alice.create_transaction(bob.get_address())
    assert tx is not None
    assert bank.add_transaction_to_mempool(tx)
    assert not bank.add_transaction_to_mempool(tx)
    assert bank.get_mempool() == [tx]


def test_spend_coin_not_mine(bank2: Bank, alice: Wallet, bob: Wallet, alice_coin: Transaction) -> None:
    tx = alice.create_transaction(bob.get_address())
    assert tx is not None
    assert not bank2.add_transaction_to_mempool(tx)
    assert not bank2.get_mempool()


def test_change_output_of_signed_transaction(bank: Bank, alice: Wallet, bob: Wallet, charlie: Wallet,
                                             alice_coin: Transaction) -> None:
    tx = alice.create_transaction(bob.get_address())
    print(f"alice txid: {tx.get_txid()}")
    assert tx is not None
    tx = Transaction(output=charlie.get_address(),
                     input=tx.input, signature=tx.signature)
    print(f"charlie txid: {tx.get_txid()})")
    assert not bank.add_transaction_to_mempool(tx)
    assert not bank.get_mempool()
    bank.end_day()
    alice.update(bank)
    bob.update(bank)
    assert alice.get_balance() == 1
    assert bob.get_balance() == 0
    assert charlie.get_balance() == 0


def test_change_coin_of_signed_transaction(bank: Bank, alice: Wallet, bob: Wallet, charlie: Wallet,
                                           alice_coin: Transaction) -> None:
    print("Initial state:")
    print(f"Alice UTXOs: {alice.utxos}")
    print(f"Bob UTXOs: {bob.utxos}")
    print(f"Bank Mempool: {len(bank.mem_pool)}")

    # Give Bob a coin from Alice
    tx = alice.create_transaction(bob.get_address())
    assert tx is not None, "Transaction creation failed"

    print("After Alice's transaction:")
    print(f"Transaction target: {tx.output}")
    print(f"Transaction input: {tx.input}")

    bank.add_transaction_to_mempool(tx)
    print(f"Bank Mempool after add: {len(bank.mem_pool)}")

    # Create one more coin for Bob from the bank
    bank.create_money(bob.get_address())
    print(f"Bank Mempool after create_money: {len(bank.mem_pool)}")

    bank.end_day()
    print(f"Blockchain length: {len(bank.blockchain)}")
    print(f"Last block transactions: {[tx.output for tx in bank.blockchain[-1].get_transactions()]}")

    alice.update(bank)
    bob.update(bank)
    charlie.update(bank)

    print("\nAfter updates:")
    print(f"Alice UTXOs: {alice.utxos}")
    print(f"Bob UTXOs: {bob.utxos}")

    # Debug: Inspect UTXOs
    utxos = bank.get_utxo()
    print("\nAll UTXOs:")
    for utxo in utxos:
        print(f"UTXO: {utxo}, Output: {utxo.output}")

    # Check number of UTXOs
    print(f"Total UTXOs: {len(utxos)}")
    bob_coin1, bob_coin2 = bank.get_utxo()
    # Bob gives a coin to Charlie, and Charlie wants to steal the second one
    tx = bob.create_transaction(charlie.get_address())
    assert tx is not None
    tx2 = Transaction(output=tx.output, input=bob_coin2.get_txid() if tx.input == bob_coin1.get_txid()
                      else bob_coin1.get_txid(), signature=tx.signature)
    assert not bank.add_transaction_to_mempool(tx2)
    assert not bank.get_mempool()
    assert bank.add_transaction_to_mempool(tx)
    assert bank.get_mempool()
    bank.end_day()
    alice.update(bank)
    bob.update(bank)
    charlie.update(bank)
    assert alice.get_balance() == 0
    assert bob.get_balance() == 1
    assert charlie.get_balance() == 1


def test_double_spend_fail(bank: Bank, alice: Wallet, bob: Wallet, charlie: Wallet, alice_coin: Transaction) -> None:
    tx1 = alice.create_transaction(bob.get_address())
    assert tx1 is not None
    # make alice spend the same coin
    alice.update(bank)
    alice.unfreeze_all()
    tx2 = alice.create_transaction(charlie.get_address())
    assert tx2 is not None  # Alice will try to double spend

    assert bank.add_transaction_to_mempool(tx1)
    assert not bank.add_transaction_to_mempool(tx2)
    bank.end_day(limit=2)
    alice.update(bank)
    bob.update(bank)
    charlie.update(bank)
    assert alice.get_balance() == 0
    assert bob.get_balance() == 1
    assert charlie.get_balance() == 0


def test_empty_blockchain(bank: Bank) -> None:
    assert bank.get_latest_hash() == GENESIS_BLOCK_PREV
    assert not bank.get_mempool()
    assert not bank.get_utxo()


def test_multiple_coin_creation(bank: Bank, alice: Wallet, bob: Wallet) -> None:
    bank.create_money(alice.get_address())
    bank.create_money(bob.get_address())
    bank.end_day()
    alice.update(bank)
    bob.update(bank)
    utxo = bank.get_utxo()
    assert len(utxo) == 2
    assert utxo[0].output == alice.get_address()
    assert utxo[1].output == bob.get_address()


def test_invalid_signature(bank: Bank, alice: Wallet, bob: Wallet, alice_coin: Transaction) -> None:
    tx = alice.create_transaction(bob.get_address())
    assert tx is not None
    # Tamper with the signature
    tx.signature = b"fake_signature"
    assert not bank.add_transaction_to_mempool(tx)
    assert not bank.get_mempool()


def test_transaction_ordering(bank: Bank, alice: Wallet, bob: Wallet, charlie: Wallet, alice_coin: Transaction) -> None:
    bank.create_money(alice.get_address())
    bank.create_money(bob.get_address())

    bank.end_day()

    alice.update(bank)
    bob.update(bank)
    charlie.update(bank)

    tx1 = alice.create_transaction(bob.get_address())
    tx2 = bob.create_transaction(charlie.get_address())
    assert bank.add_transaction_to_mempool(tx1)
    assert bank.add_transaction_to_mempool(tx2)

    bank.end_day(limit=2)
    alice.update(bank)
    bob.update(bank)
    charlie.update(bank)
    block = bank.get_block(bank.get_latest_hash())
    transactions = block.get_transactions()
    assert len(transactions) == 2
    assert transactions[0] == tx1
    assert transactions[1] == tx2


def test_transaction_with_no_coin(bank: Bank, alice: Wallet, bob: Wallet) -> None:
    tx = alice.create_transaction(bob.get_address())
    assert tx is None
    assert not bank.add_transaction_to_mempool(tx)
    assert not bank.get_mempool()


def test_large_mempool(bank: Bank, alice: Wallet, bob: Wallet) -> None:
    for _ in range(100):
        bank.create_money(alice.get_address())
        bank.end_day()
        alice.update(bank)
    for i in range(100):
        tx = alice.create_transaction(bob.get_address())
        assert tx is not None
        bank.end_day()
        print(i)
        assert bank.add_transaction_to_mempool(tx)
    bank.end_day()
    alice.update(bank)
    bob.update(bank)
    assert alice.get_balance() == 0
    assert bob.get_balance() == 100
    assert not bank.get_mempool()
    assert len(bank.get_utxo()) == 100


def test_double_spend_across_blocks(bank: Bank, alice: Wallet, bob: Wallet, alice_coin: Transaction) -> None:
    bank.create_money(alice.get_address())
    tx1 = alice.create_transaction(bob.get_address())
    assert bank.add_transaction_to_mempool(tx1)
    bank.end_day(limit=1)
    tx2 = alice.create_transaction(bob.get_address())  # Attempt to spend the same coin again
    assert not bank.add_transaction_to_mempool(tx2)

def test_create_money_for_multiple_wallets(bank: Bank, alice: Wallet, bob: Wallet, charlie: Wallet) -> None:
    bank.create_money(alice.get_address())
    bank.create_money(bob.get_address())
    bank.create_money(charlie.get_address())
    bank.end_day()
    alice.update(bank)
    bob.update(bank)
    charlie.update(bank)
    assert alice.get_balance() == 1
    assert bob.get_balance() == 1
    assert charlie.get_balance() == 1


def test_transaction_with_insufficient_balance(bank: Bank, alice: Wallet, bob: Wallet, alice_coin: Transaction) -> None:
    tx = alice.create_transaction(bob.get_address())
    assert tx is not None
    bank.add_transaction_to_mempool(tx)
    bank.end_day()
    alice.update(bank)
    bob.update(bank)
    assert alice.get_balance() == 0
    assert bob.get_balance() == 1

    tx2 = alice.create_transaction(bob.get_address())
    assert tx2 is None  # Alice has no balance to create a new transaction


def test_transaction_with_invalid_input(bank: Bank, alice: Wallet, bob: Wallet, alice_coin: Transaction) -> None:
    tx = alice.create_transaction(bob.get_address())
    assert tx is not None
    bank.add_transaction_to_mempool(tx)
    bank.end_day()
    alice.update(bank)
    bob.update(bank)

    tampered_tx = Transaction(output=bob.get_address(), input=bytes(1), signature=tx.signature)
    assert not bank.add_transaction_to_mempool(tampered_tx)
    assert not bank.get_mempool()


def test_transaction_with_invalid_output(bank: Bank, alice: Wallet, bob: Wallet, alice_coin: Transaction) -> None:
    tx = alice.create_transaction(bob.get_address())
    assert tx is not None
    bank.add_transaction_to_mempool(tx)
    bank.end_day()
    alice.update(bank)
    bob.update(bank)

    tampered_tx = Transaction(output=bytes(1), input=tx.input, signature=tx.signature)
    assert not bank.add_transaction_to_mempool(tampered_tx)
    assert not bank.get_mempool()


def test_transaction_with_invalid_signature(bank: Bank, alice: Wallet, bob: Wallet, alice_coin: Transaction) -> None:
    tx = alice.create_transaction(bob.get_address())
    assert tx is not None
    bank.add_transaction_to_mempool(tx)
    bank.end_day()
    alice.update(bank)
    bob.update(bank)

    tampered_tx = Transaction(output=bob.get_address(), input=tx.input, signature=b"invalid_signature")
    assert not bank.add_transaction_to_mempool(tampered_tx)
    assert not bank.get_mempool()


def test_transaction_with_multiple_inputs(bank: Bank, alice: Wallet, bob: Wallet, charlie: Wallet, alice_coin: Transaction) -> None:
    tx1 = alice.create_transaction(bob.get_address())
    assert tx1 is not None
    bank.add_transaction_to_mempool(tx1)
    bank.create_money(alice.get_address())
    bank.end_day()
    alice.update(bank)
    bob.update(bank)

    tx2 = alice.create_transaction(charlie.get_address())

    assert tx2 is not None
    bank.add_transaction_to_mempool(tx2)
    bank.end_day()
    alice.update(bank)
    charlie.update(bank)
    assert alice.get_balance() == 0
    assert bob.get_balance() == 1
    assert charlie.get_balance() == 1


def test_transaction_with_multiple_signatures(bank: Bank, alice: Wallet, bob: Wallet, charlie: Wallet, alice_coin: Transaction) -> None:
    tx1 = alice.create_transaction(bob.get_address())
    assert tx1 is not None
    bank.add_transaction_to_mempool(tx1)
    bank.end_day()
    alice.update(bank)
    bob.update(bank)

    tx2 = bob.create_transaction(charlie.get_address())
    assert tx2 is not None
    bank.add_transaction_to_mempool(tx2)
    bank.end_day()
    bob.update(bank)
    charlie.update(bank)
    assert alice.get_balance() == 0
    assert bob.get_balance() == 0
    assert charlie.get_balance() == 1


def test_transaction_with_no_signature(bank: Bank, alice: Wallet, bob: Wallet, alice_coin: Transaction) -> None:
    tx = alice.create_transaction(bob.get_address())
    assert tx is not None
    tampered_tx = Transaction(output=tx.output, input=tx.input, signature=None)
    assert not bank.add_transaction_to_mempool(tampered_tx)
    assert not bank.get_mempool()


def test_transaction_with_no_input(bank: Bank, alice: Wallet, bob: Wallet, alice_coin: Transaction) -> None:
    tx = alice.create_transaction(bob.get_address())
    assert tx is not None
    tampered_tx = Transaction(output=tx.output, input=None, signature=tx.signature)
    assert not bank.add_transaction_to_mempool(tampered_tx)
    assert not bank.get_mempool()