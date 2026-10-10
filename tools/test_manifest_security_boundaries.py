import unittest

from verify_broker_apk import verify_manifest
from test_realistic_manifest_contract import (
    BASE,
    WITH_SDK,
)


class ManifestSecurityBoundaries(unittest.TestCase):

    def assert_rejected(self, manifest):
        with self.assertRaises(ValueError):
            verify_manifest(manifest)

    def test_duplicate_namespace_rejected(self):
        self.assert_rejected(
            BASE.replace(
                "N: android=http://schemas.android.com/apk/res/android",
                "N: android=http://schemas.android.com/apk/res/android\n"
                "N: android=http://schemas.android.com/apk/res/android",
            )
        )

    def test_namespace_after_root_rejected(self):
        self.assert_rejected(
            BASE.replace(
                "N: android=http://schemas.android.com/apk/res/android\n",
                "",
            )
            + "\nN: android=http://schemas.android.com/apk/res/android\n"
        )

    def test_duplicate_package_rejected(self):
        self.assert_rejected(
            BASE.replace(
                'A: package="com.sophyane.rsi.broker" '
                '(Raw: "com.sophyane.rsi.broker")',
                'A: package="com.sophyane.rsi.broker" '
                '(Raw: "com.sophyane.rsi.broker")\n'
                '    A: package="com.sophyane.rsi.broker" '
                '(Raw: "com.sophyane.rsi.broker")',
            )
        )

    def test_wrong_sdk_version_rejected(self):
        self.assert_rejected(
            WITH_SDK.replace(
                "(type 0x10)0x24",
                "(type 0x10)0x23",
            )
        )

    def test_missing_target_sdk_rejected(self):
        self.assert_rejected(
            "\n      A: android:targetSdkVersion"
            "(0x01010270)=(type 0x10)0x24",
        ) if False else None

        self.assert_rejected(
            WITH_SDK.replace(
                "      A: android:targetSdkVersion"
                "(0x01010270)=(type 0x10)0x24\n",
                "",
            )
        )

    def test_missing_min_sdk_rejected(self):
        self.assert_rejected(
            WITH_SDK.replace(
                "      A: android:minSdkVersion"
                "(0x0101020c)=(type 0x10)0x1a\n",
                "",
            )
        )

    def test_unknown_application_attribute_rejected(self):
        self.assert_rejected(
            BASE.replace(
                "      A: android:hasCode",
                "      A: android:permission"
                "(0x01010006)=(type 0x03)0x7f000000\n"
                "      A: android:hasCode",
            )
        )

    def test_security_attribute_wrong_element_rejected(self):
        self.assert_rejected(
            WITH_SDK.replace(
                "      A: android:minSdkVersion",
                "      A: android:debuggable"
                "(0x0101000f)=(type 0x12)0x0\n"
                "      A: android:minSdkVersion",
            )
        )

    def test_duplicate_security_attribute_rejected(self):
        self.assert_rejected(
            BASE.replace(
                "      A: android:debuggable"
                "(0x0101000f)=(type 0x12)0x0",
                "      A: android:debuggable"
                "(0x0101000f)=(type 0x12)0x0\n"
                "      A: android:debuggable"
                "(0x0101000f)=(type 0x12)0x0",
            )
        )

    def test_unknown_manifest_element_rejected(self):
        self.assert_rejected(
            BASE.replace(
                "    E: application",
                "    E: uses-permission\n"
                "    E: application",
            )
        )

    def test_malformed_record_rejected(self):
        self.assert_rejected(
            BASE + "\n  A: android:debuggable=FALSE\n"
        )


if __name__ == "__main__":
    unittest.main()
