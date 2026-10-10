import unittest

from verify_broker_apk import verify_manifest

FALSE_ATTRIBUTES = """
    A: android:allowBackup(0x01010280)=(type 0x12)0x0
    A: android:debuggable(0x0101000f)=(type 0x12)0x0
    A: android:hasCode(0x0101000c)=(type 0x12)0x0
    A: android:usesCleartextTraffic(0x010104ec)=(type 0x12)0x0
"""


class AdversarialManifestTests(unittest.TestCase):

    def assert_rejected(self, manifest):
        with self.assertRaises(ValueError):
            verify_manifest(manifest)

    def test_attributes_on_wrong_element(self):
        self.assert_rejected(
            "E: manifest\n"
            + FALSE_ATTRIBUTES
            + "  E: application\n"
        )

    def test_duplicate_conflicting_attribute(self):
        self.assert_rejected(
            "E: manifest\n"
            "  E: application\n"
            + FALSE_ATTRIBUTES
            + "    A: android:debuggable"
            "(0x0101000f)=(type 0x12)0xffffffff\n"
        )

    def test_unexpected_manifest_element(self):
        self.assert_rejected(
            "E: manifest\n"
            "  E: application\n"
            + FALSE_ATTRIBUTES
            + "    E: unknown-executable-component\n"
        )

    def test_malformed_manifest_structure(self):
        self.assert_rejected(FALSE_ATTRIBUTES)

    def test_nested_component(self):
        self.assert_rejected(
            "E: manifest\n"
            "  E: application\n"
            + FALSE_ATTRIBUTES
            + "      E: receiver\n"
        )


if __name__ == "__main__":
    unittest.main()
