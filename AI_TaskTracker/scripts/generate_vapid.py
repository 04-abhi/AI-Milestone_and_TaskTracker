import os
from pywebpush import webpush
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization

ENV_FILE = ".env"


def generate_vapid_keys():
    private_key = ec.generate_private_key(ec.SECP256R1())

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode()

    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()

    return public_pem, private_pem


def ensure_vapid_keys():
    from dotenv import load_dotenv
    load_dotenv()

    public = os.getenv("VAPID_PUBLIC_KEY")
    private = os.getenv("VAPID_PRIVATE_KEY")

    if public and private:
        print("VAPID keys already exist.")
        return

    print("Generating VAPID keys...")

    public_key, private_key = generate_vapid_keys()

    with open(ENV_FILE, "a") as f:
        f.write(f"\nVAPID_PUBLIC_KEY={repr(public_key)}\n")
        f.write(f"VAPID_PRIVATE_KEY={repr(private_key)}\n")

    print("VAPID keys generated and saved.")