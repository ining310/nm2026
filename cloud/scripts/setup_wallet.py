"""
Generate a new IOTA Ed25519 machine wallet and fund it from the devnet faucet.

Run ONCE before first deployment:
    cd /path/to/wm2026
    python cloud/scripts/setup_wallet.py

Output:
    - Prints the private key hex (copy to .env and AWS SSM)
    - Prints the machine wallet address
    - Optionally funds from the devnet faucet
"""
import hashlib
import secrets
import sys

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

FAUCET_URL    = "https://faucet.devnet.iota.cafe"  # web-only; requires Turnstile CAPTCHA
EXPLORER_BASE = "https://explorer.rebased.iota.org"
NETWORK       = "devnet"


def generate_keypair() -> tuple[str, str]:
    """Return (private_key_hex, iota_address)."""
    pk_bytes = secrets.token_bytes(32)
    priv     = Ed25519PrivateKey.from_private_bytes(pk_bytes)
    pub      = priv.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    addr     = "0x" + hashlib.blake2b(bytes([0x00]) + pub, digest_size=32).hexdigest()
    return pk_bytes.hex(), addr


def fund_faucet(address: str) -> bool:
    """
    The devnet faucet (faucet.devnet.iota.cafe) now requires a Cloudflare
    Turnstile CAPTCHA token, so it cannot be called programmatically.
    Direct the user to the web UI instead.
    """
    print(f"\nThe faucet requires a browser CAPTCHA (Cloudflare Turnstile).")
    print(f"Open the faucet in your browser and paste the address below:")
    print(f"\n  {FAUCET_URL}")
    print(f"\n  Address: {address}")
    return False


def main():
    priv_hex, address = generate_keypair()

    print("=" * 64)
    print("  NEW MACHINE WALLET")
    print("=" * 64)
    print(f"\n  Address : {address}")
    print(f"\n  Private key (hex) — add to .env and AWS SSM Parameter Store:")
    print(f"\n  IOTA_MACHINE_PRIVATE_KEY_HEX={priv_hex}")
    print(f"\n  Explorer: {EXPLORER_BASE}/address/{address}?network={NETWORK}")
    print()
    print("  ⚠️  SAVE the private key SECURELY. Do NOT commit it to git.")
    print("=" * 64)

    ans = input("\nFund from devnet faucet now? [Y/n] ").strip().lower()
    if ans != "n":
        ok = fund_faucet(address)
        print(f"\nCheck balance at:")
        print(f"{EXPLORER_BASE}/address/{address}?network={NETWORK}")
        if not ok:
            print("\nIf faucet failed, open the URL above and use the web faucet.")

    print("\nNext step: follow WALKTHROUGH.md § 2 to store the key in AWS SSM.")


if __name__ == "__main__":
    main()
