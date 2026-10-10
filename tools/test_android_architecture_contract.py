"""Phase 100 design-only guardrails; not Android runtime integration tests."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCH = ROOT / "docs" / "phase-100-android-security-architecture.md"

class AndroidArchitectureContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = ARCH.read_text(encoding="utf-8")

    def test_design_only_gate(self):
        self.assertIn("DESIGN-ONLY / NO RUNTIME AUTHORITY", self.text)
        self.assertIn("no approved Android IPC transport", self.text)

    def test_os_caller_identity_required(self):
        self.assertIn("OS-reported Binder calling UID", self.text)
        self.assertIn("caller-supplied UID", self.text)
        self.assertIn("multiple users/work profiles", self.text)

    def test_verifier_independence_required(self):
        self.assertIn("keys are inaccessible to the proposer", self.text)
        self.assertIn("self-reported", self.text)
        self.assertIn("immutable", self.text)

    def test_rollback_is_unresolved(self):
        self.assertIn("do not claim rollback resistance", self.text)
        self.assertIn("external trusted anchor", self.text)

    def test_real_android_evidence_required(self):
        self.assertIn("Real Binder negative tests", self.text)
        self.assertIn("Controlled-device proof of distinct UIDs", self.text)
        self.assertIn("Explicit human authorization", self.text)

    def test_no_execution_authority(self):
        self.assertIn("No arbitrary shell/Git commands", self.text)
        self.assertIn("no modification of production Sophyane", self.text)
        self.assertIn("no signing or installation of the inert APK", self.text)

if __name__ == "__main__":
    unittest.main()
