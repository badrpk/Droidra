import unittest

from verify_broker_apk import verify_manifest

ATTRS = """
    A: android:allowBackup(0x01010280)=(type 0x12)0x0
    A: android:debuggable(0x0101000f)=(type 0x12)0x0
    A: android:hasCode(0x0101000c)=(type 0x12)0x0
    A: android:usesCleartextTraffic(0x010104ec)=(type 0x12)0x0
"""

GOOD = "E: manifest\n  E: application\n" + ATTRS


class ExtendedManifestTests(unittest.TestCase):

    def rejected(self, value):
        with self.assertRaises(ValueError):
            verify_manifest(value)

    def test_valid_baseline(self):
        verify_manifest(GOOD)

    def test_application_at_root_level(self):
        self.rejected(
            "E: manifest\nE: application\n" + ATTRS
        )

    def test_duplicate_root_attribute(self):
        self.rejected(
            "E: manifest\n"
            "  A: android:versionCode(0x0101021b)=(type 0x10)0x1\n"
            "  A: android:versionCode(0x0101021b)=(type 0x10)0x2\n"
            "  E: application\n" + ATTRS
        )

    def test_application_attribute_wrong_indentation(self):
        self.rejected(
            "E: manifest\n"
            "  E: application\n"
            "  A: android:allowBackup(0x01010280)=(type 0x12)0x0\n"
            + ATTRS.replace(
                "android:allowBackup(0x01010280)=(type 0x12)0x0",
                "",
            )
        )

    def test_trailing_malformed_record(self):
        self.rejected(
            GOOD + "\n    A: android:debuggable MALFORMED\n"
        )

    def test_second_manifest_root(self):
        self.rejected(
            GOOD + "\nE: manifest\n"
        )


if __name__ == "__main__":
    unittest.main()
