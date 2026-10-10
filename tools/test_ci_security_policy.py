import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

WORKFLOW = (
    ROOT
    / ".github/workflows/build-sophyane-rsi-broker.yml"
)

APP = (
    ROOT
    / "apps/sophyane-rsi-broker/app/build.gradle.kts"
)

MANIFEST = (
    ROOT
    / "apps/sophyane-rsi-broker/app/src/main/AndroidManifest.xml"
)


class BrokerCIPolicyTests(unittest.TestCase):

    def test_no_debug_apk_build(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertNotRegex(
            workflow,
            r"\bassembleDebug\b",
        )

    def test_no_debug_apk_upload(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertNotIn(
            "app-debug.apk",
            workflow,
        )

    def test_compiled_verifier_invoked(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertRegex(
            workflow,
            r"python3?\s+.*verify_broker_apk\.py",
        )

    def test_source_manifest_inert(self):
        manifest = MANIFEST.read_text(encoding="utf-8")

        for attribute in (
            "allowBackup",
            "hasCode",
            "usesCleartextTraffic",
        ):
            self.assertRegex(
                manifest,
                rf'android:{attribute}="false"',
            )

        # Android defaults debuggable to false; explicit false fails Lint.
        # Reject explicit true and rely on compiled-manifest verification.
        self.assertNotRegex(
            manifest,
            r'android:debuggable\\s*=\\s*"true"',
        )

        self.assertNotRegex(
            manifest,
            r"<\s*(activity|service|receiver|provider)\b",
        )

        self.assertNotRegex(
            manifest,
            r"<\s*uses-permission\b",
        )

    def test_app_identity(self):
        config = APP.read_text(encoding="utf-8")

        self.assertIn(
            'applicationId = "com.sophyane.rsi.broker"',
            config,
        )

        self.assertIn(
            "targetSdk = 36",
            config,
        )

    def test_workflow_read_only_permissions(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")

        self.assertRegex(
            workflow,
            r"(?m)^permissions:\s*\n"
            r"\s+contents:\s*read\s*$",
        )

    def test_manual_workflow_trigger(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")

        self.assertRegex(
            workflow,
            r"(?m)^\s+workflow_dispatch:\s*$",
        )


if __name__ == "__main__":
    unittest.main()
