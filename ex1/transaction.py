from .utils import PublicKey, TxID, Signature
from typing import Optional
import hashlib


class Transaction:
    """Represents a transaction that moves a single coin
    A transaction with no source creates money. It will only be created by the bank."""

    def __init__(self, output: PublicKey, input: Optional[TxID], signature: Signature) -> None:
        # Public key of the recipient of the coin
        self.output: PublicKey = output
        # Transaction ID of previous transaction
        self.input: Optional[TxID] = input
        # do not change the name of this field:
        self.signature: Signature = signature
        self._tx_id = self.get_txid()

    def get_txid(self) -> TxID:
        """Returns the identifier of this transaction. This is the SHA256 of the transaction contents."""
        input_bytes = self.input if self.input is not None else b""
        output_bytes = self.output if self.output is not None else b""
        input_bytes += output_bytes
        hashed_input = hashlib.sha256(input_bytes).digest()
        return TxID(hashed_input)
