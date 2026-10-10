import unittest

from verify_broker_apk import (
    verify_badging,
    verify_permissions,
    verify_manifest,
)

GOOD_MANIFEST = """
E: manifest
  E: application
    A: android:allowBackup(0x01010280)=(type 0x12)0x0
    A: android:debuggable(0x0101000f)=(type 0x12)0x0
    A: android:hasCode(0x0101000c)=(type 0x12)0x0
    A: android:usesCleartextTraffic(0x010104ec)=(type 0x12)0x0
"""


class BrokerVerifierTests(unittest.TestCase):

    def test_valid_package(self):
        verify_badging(
            "package: name='com.sophyane.rsi.broker'"
        )

    def test_wrong_package_rejected(self):
        with self.assertRaises(ValueError):
            verify_badging(
                "package: name='com.attacker.broker'"
            )

    def test_permission_rejected(self):
        with self.assertRaises(ValueError):
            verify_permissions(
                "uses-permission: name='android.permission.INTERNET'"
            )

    def test_valid_manifest(self):
        verify_manifest(GOOD_MANIFEST)

    def test_backup_enabled_rejected(self):
        with self.assertRaises(ValueError):
            verify_manifest(
                GOOD_MANIFEST.replace(
                    "android:allowBackup(0x01010280)=(type 0x12)0x0",
                    "android:allowBackup(0x01010280)=(type 0x12)0xffffffff",
                )
            )

    def test_component_rejected(self):
        with self.assertRaises(ValueError):
            verify_manifest(
                GOOD_MANIFEST + "\n  E: service\n"
            )

    def test_missing_attribute_rejected(self):
        with self.assertRaises(ValueError):
            verify_manifest(
                GOOD_MANIFEST.replace(
                    "android:hasCode(0x0101000c)=(type 0x12)0x0",
                    "",
                )
            )


if __name__ == "__main__":
    unittest.main()
