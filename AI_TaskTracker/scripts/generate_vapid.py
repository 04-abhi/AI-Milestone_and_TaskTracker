"""
VAPID Key Generator
--------------------
Run this ONCE to generate your Web Push notification keys.
Then paste the output into your .env file.

Usage:
    python scripts/generate_vapid.py
"""
import sys
import base64

try:
    from pywebpush import Vapid
except ImportError:
    print("ERROR: pywebpush not installed. Run: pip install pywebpush")
    sys.exit(1)

v = Vapid()
v.generate_keys()

# Export private key as PEM string (single line for .env)
private_pem = v.private_pem().decode("utf-8").strip()

# Export public key as URL-safe base64 (what browsers need)
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
public_bytes = v.public_key.public_bytes(
    encoding=Encoding.X962,
    format=PublicFormat.UncompressedPoint,
)
public_b64 = base64.urlsafe_b64encode(public_bytes).rstrip(b"=").decode("utf-8")

print("\n✅  VAPID Keys Generated!")
print("=" * 60)
print("Copy these two lines into your .env file:\n")
print(f'VAPID_PRIVATE_KEY="{private_pem}"')
print(f"VAPID_PUBLIC_KEY={public_b64}")
print("\n" + "=" * 60)
print("⚠   Keep VAPID_PRIVATE_KEY secret. Never commit it to git.")
print("    The PUBLIC key is safe to share — the browser uses it.\n")
