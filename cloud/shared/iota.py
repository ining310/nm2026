"""
IOTA Rebased devnet — Ed25519 wallet + token transfer via JSON-RPC.

IOTA Rebased is Sui-compatible.  All JSON-RPC method names start with
'iota_' / 'unsafe_' instead of 'sui_'.

Signing algorithm (same as Sui):
    message  = intent_prefix (3 bytes: [0, 0, 0]) + tx_bytes
    sig_raw  = Ed25519.sign(private_key, message)   # standard Ed25519, SHA-512 internal
    envelope = 0x00 (Ed25519 flag) | sig_raw (64 B) | public_key (32 B)
    signature = base64(envelope)
"""
import base64
import hashlib
import os

import requests
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

# 3-byte intent prefix: TransactionData / V0 / Iota app-id
_INTENT = bytes([0, 0, 0])


# ── helpers ──────────────────────────────────────────────────────────────────

def _rpc(method: str, params: list) -> dict:
    url = os.environ["IOTA_RPC_URL"]
    resp = requests.post(
        url,
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"IOTA RPC error [{method}]: {data['error']}")
    return data["result"]


def _load_private_key() -> bytes:
    hex_key = os.environ["IOTA_MACHINE_PRIVATE_KEY_HEX"].strip()
    return bytes.fromhex(hex_key)


def _derive_address(private_key_bytes: bytes) -> str:
    """
    Derive an IOTA/Sui address from a 32-byte Ed25519 private key.
    address = hex( blake2b_256( 0x00 || public_key_bytes ) )
    """
    priv = Ed25519PrivateKey.from_private_bytes(private_key_bytes)
    pub  = priv.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    addr = hashlib.blake2b(bytes([0x00]) + pub, digest_size=32).digest()
    return "0x" + addr.hex()


def _sign(private_key_bytes: bytes, tx_bytes_b64: str) -> str:
    """Return a base64-encoded IOTA signature envelope."""
    tx_bytes = base64.b64decode(tx_bytes_b64)
    message  = _INTENT + tx_bytes

    priv = Ed25519PrivateKey.from_private_bytes(private_key_bytes)
    sig  = priv.sign(message)                                       # 64 bytes
    pub  = priv.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)  # 32 bytes

    # envelope: [flag=0x00] | [sig 64 B] | [pubkey 32 B]
    return base64.b64encode(bytes([0x00]) + sig + pub).decode()


# ── public API ────────────────────────────────────────────────────────────────

def get_machine_address() -> str:
    """Return the IOTA address derived from the machine wallet private key."""
    return _derive_address(_load_private_key())


def send_reward(to_address: str, amount_mist: int) -> dict:
    """
    Transfer *amount_mist* MIST (1 IOTA = 1_000_000_000 MIST) from the
    machine wallet to *to_address*.

    Returns {"digest": "...", "explorer_url": "https://..."}
    """
    pk_bytes = _load_private_key()
    sender   = _derive_address(pk_bytes)
    network  = os.environ["IOTA_NETWORK"]
    explorer = os.environ["IOTA_EXPLORER_BASE"]

    # 1. Find a gas coin owned by the machine wallet
    coins_resp = _rpc("iota_getCoins", [
        sender,
        "0x2::iota::IOTA",
        None,   # cursor
        None,   # limit (fetch first page)
    ])
    coins = coins_resp.get("data", [])
    if not coins:
        raise RuntimeError(
            f"Machine wallet ({sender}) has no IOTA coins. "
            "Run cloud/scripts/setup_wallet.py to fund it first."
        )

    # Use the coin with the largest balance (to maximise chance gas covers the tx)
    gas_coin = max(coins, key=lambda c: int(c.get("balance", 0)))

    # 2. Build the unsigned transaction (unsigned_tx_bytes returned as base64)
    tx_result = _rpc("unsafe_transferIota", [
        sender,                         # signer
        gas_coin["coinObjectId"],       # IOTAObjectId — coin used for transfer AND gas
        str(10_000_000),                # gas_budget: 0.01 IOTA (adjust if needed)
        to_address,                     # recipient
        str(amount_mist),               # amount in MIST
    ])
    tx_bytes_b64 = tx_result["txBytes"]

    # 3. Sign
    signature = _sign(pk_bytes, tx_bytes_b64)

    # 4. Execute
    exec_result = _rpc("iota_executeTransactionBlock", [
        tx_bytes_b64,
        [signature],
        {"showEffects": True, "showObjectChanges": True},
        "WaitForLocalExecution",
    ])

    digest       = exec_result["digest"]
    explorer_url = f"{explorer}/txblock/{digest}?network={network}"
    return {"digest": digest, "explorer_url": explorer_url}


def request_faucet(address: str | None = None) -> str:
    """
    Request devnet tokens from the faucet for *address* (or the machine wallet).
    Call once during initial setup (see cloud/scripts/setup_wallet.py).
    """
    if address is None:
        address = get_machine_address()
    faucet_url = os.environ["IOTA_FAUCET_URL"]
    resp = requests.post(
        faucet_url,
        json={"FixedAmountRequest": {"recipient": address}},
        timeout=30,
    )
    resp.raise_for_status()
    return address
