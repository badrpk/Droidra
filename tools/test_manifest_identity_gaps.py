import unittest

from verify_broker_apk import verify_manifest
from test_realistic_manifest_contract import BASE


class ManifestIdentityGaps(unittest.TestCase):

    def assert_rejected(self, manifest):
        with self.assertRaises(ValueError):
            verify_manifest(manifest, strict=True)

    def test_missing_package_identity(self):
        lines = [
            line for line in BASE.splitlines()
            if 'A: package=' not in line
        ]
        self.assert_rejected("\n".join(lines) + "\n")

    def test_missing_namespace(self):
        lines = [
            line for line in BASE.splitlines()
            if not line.startswith("N: android=")
        ]
        self.assert_rejected("\n".join(lines) + "\n")

    def test_unexpected_manifest_attribute(self):
        mutated = BASE.replace(
            "    E: application",
            "    A: android:sharedUserId"
            "(0x0101000b)=(type 0x03)0x7f000001\n"
            "    E: application",
        )
        self.assertNotEqual(mutated, BASE)
        self.assert_rejected(mutated)

    def test_forged_debuggable_resource_id(self):
        mutated = BASE.replace(
            "android:debuggable(0x0101000f)",
            "android:debuggable(0x01019999)",
        )
        self.assertNotEqual(mutated, BASE)
        self.assert_rejected(mutated)

    def test_forged_backup_resource_id(self):
        mutated = BASE.replace(
            "android:allowBackup(0x01010280)",
            "android:allowBackup(0x01019999)",
        )
        self.assertNotEqual(mutated, BASE)
        self.assert_rejected(mutated)

    def test_duplicate_manifest_package(self):
        package = (
            '    A: package="com.sophyane.rsi.broker" '
            '(Raw: "com.sophyane.rsi.broker")'
        )
        self.assertIn(package, BASE)

        mutated = BASE.replace(
            package,
            package + "\n" + package,
        )
        self.assert_rejected(mutated)


if __name__ == "__main__":
    unittest.main()
