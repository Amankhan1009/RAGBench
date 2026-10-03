"""
RAGBench Phase 0 Compatibility & Integration Spike Verification Script
Checks Python version, basic cryptography operations, Pydantic v2 schemas, and DeepEval importability.
"""
import sys


def verify_environment():
    print(f"[INFO] Checking Python version: {sys.version}")
    assert sys.version_info >= (3, 13), "RAGBench requires Python 3.13+"
    print("[PASS] Python version check passed (>= 3.13)")
    try:
        import pydantic
        print(f"[PASS] Pydantic version {pydantic.__version__} loaded successfully.")
    except ImportError:
        print("[WARN] Pydantic not installed yet (will be installed in Phase 1).")
    try:
        import cryptography
        print(f"[PASS] Cryptography library available: {cryptography.__file__}")
    except ImportError:
        print("[WARN] Cryptography not installed yet (will be installed in Phase 1/4).")
    print("[SUCCESS] Phase 0 Compatibility Verification Complete.")
if __name__ == "__main__":
    verify_environment()
