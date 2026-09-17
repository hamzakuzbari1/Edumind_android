import bcrypt
from passlib.context import CryptContext

OLD = "$2b$12$VoS2S3DrHNq2Wsf/L1K6yeCjv1IIeIu8SXi5e6LsrRpbEn8ZDingu"
CUR = "$2b$12$1yL8ChXevqTF5ZdV2rCS4Of2WlFlBv3lZ5/C8ZZxxI7dS3CiaZJWO"

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

for label, h in [("old", OLD), ("cur", CUR)]:
    print(f"=== {label} ===")
    for pw in ["123456", "student123"]:
        try:
            print("passlib", pw, pwd.verify(pw, h))
        except Exception as exc:
            print("passlib", pw, "ERR", exc)
        try:
            print("bcrypt", pw, bcrypt.checkpw(pw.encode(), h.encode()))
        except Exception as exc:
            print("bcrypt", pw, "ERR", exc)
