import hashlib
from pathlib import Path

TEST_FILE = Path("tests/fixtures/change_test.txt")


def calculate_sha256(content):
    return hashlib.sha256(content).hexdigest()


def main():
    # Read the original test document.
    original_content = TEST_FILE.read_bytes()
    original_hash = calculate_sha256(original_content)

    print("Original SHA-256:")
    print(original_hash)

    # Simulate an updated document.
    updated_content = (
        original_content + b"\n\nVersion: 2\n" + b"An amendment has been added."
    )

    updated_hash = calculate_sha256(updated_content)

    print("\nUpdated SHA-256:")
    print(updated_hash)

    # Compare fingerprints.
    if original_hash != updated_hash:
        print("\nSUCCESS: Document modification detected!")
    else:
        print("\nERROR: Modification was not detected.")


if __name__ == "__main__":
    main()
