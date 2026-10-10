"""Regression fixture captured from GitHub Actions Build #9 aapt xmltree."""
import unittest
from verify_broker_apk import verify_manifest

COMPILED = """N: android=http://schemas.android.com/apk/res/android
  E: manifest (line=2)
    A: android:versionCode(0x0101021b)=(type 0x10)0x1
    A: android:versionName(0x0101021c)="0.1.0" (Raw: "0.1.0")
    A: android:compileSdkVersion(0x01010572)=(type 0x10)0x24
    A: android:compileSdkVersionCodename(0x01010573)="16" (Raw: "16")
    A: package="com.sophyane.rsi.broker" (Raw: "com.sophyane.rsi.broker")
    A: platformBuildVersionCode=(type 0x10)0x24
    A: platformBuildVersionName=(type 0x10)0x10
    E: uses-sdk (line=7)
      A: android:minSdkVersion(0x0101020c)=(type 0x10)0x1a
      A: android:targetSdkVersion(0x01010270)=(type 0x10)0x24
    E: application (line=11)
      A: android:hasCode(0x0101000c)=(type 0x12)0x0
      A: android:allowBackup(0x01010280)=(type 0x12)0x0
      A: android:extractNativeLibs(0x010104ea)=(type 0x12)0x0
      A: android:usesCleartextTraffic(0x010104ec)=(type 0x12)0x0
"""

class ActualCompiledManifestTests(unittest.TestCase):
    def reject_mutation(self, before, after):
        self.assertIn(before, COMPILED)
        with self.assertRaises(ValueError):
            verify_manifest(COMPILED.replace(before, after, 1), strict=True)

    def test_actual_compiled_manifest_passes(self):
        verify_manifest(COMPILED, strict=True)

    def test_debuggable_true_rejected(self):
        self.reject_mutation(
            '      A: android:hasCode(0x0101000c)=(type 0x12)0x0',
            '      A: android:debuggable(0x0101000f)=(type 0x12)0x1\n'
            '      A: android:hasCode(0x0101000c)=(type 0x12)0x0',
        )

    def test_debuggable_false_explicit_accepted(self):
        manifest = COMPILED.replace(
            '      A: android:hasCode(0x0101000c)=(type 0x12)0x0',
            '      A: android:debuggable(0x0101000f)=(type 0x12)0x0\n'
            '      A: android:hasCode(0x0101000c)=(type 0x12)0x0',
        )
        verify_manifest(manifest, strict=True)

    def test_backup_true_rejected(self):
        self.reject_mutation(
            'android:allowBackup(0x01010280)=(type 0x12)0x0',
            'android:allowBackup(0x01010280)=(type 0x12)0x1',
        )

    def test_has_code_true_rejected(self):
        self.reject_mutation(
            'android:hasCode(0x0101000c)=(type 0x12)0x0',
            'android:hasCode(0x0101000c)=(type 0x12)0x1',
        )

    def test_cleartext_true_rejected(self):
        self.reject_mutation(
            'android:usesCleartextTraffic(0x010104ec)=(type 0x12)0x0',
            'android:usesCleartextTraffic(0x010104ec)=(type 0x12)0x1',
        )

    def test_extract_native_libs_true_rejected(self):
        self.reject_mutation(
            'android:extractNativeLibs(0x010104ea)=(type 0x12)0x0',
            'android:extractNativeLibs(0x010104ea)=(type 0x12)0x1',
        )

    def test_extra_component_rejected(self):
        self.reject_mutation(
            '    E: application (line=11)',
            '    E: application (line=11)\n      E: service (line=12)',
        )

    def test_extra_permission_rejected(self):
        self.reject_mutation(
            '    E: uses-sdk (line=7)',
            '    E: uses-permission (line=6)\n'
            '      A: android:name(0x01010003)="android.permission.INTERNET" '
            '(Raw: "android.permission.INTERNET")\n'
            '    E: uses-sdk (line=7)',
        )

    def test_wrong_sdk_rejected(self):
        self.reject_mutation(
            'android:targetSdkVersion(0x01010270)=(type 0x10)0x24',
            'android:targetSdkVersion(0x01010270)=(type 0x10)0x23',
        )

    def test_wrong_compile_sdk_rejected(self):
        self.reject_mutation(
            'android:compileSdkVersion(0x01010572)=(type 0x10)0x24',
            'android:compileSdkVersion(0x01010572)=(type 0x10)0x23',
        )

    def test_forged_platform_metadata_rejected(self):
        self.reject_mutation(
            'platformBuildVersionName=(type 0x10)0x10',
            'platformBuildVersionName=(type 0x10)0x11',
        )

    def test_version_name_mismatch_rejected(self):
        self.reject_mutation(
            'android:versionName(0x0101021c)="0.1.0" (Raw: "0.1.0")',
            'android:versionName(0x0101021c)="9.9.9" (Raw: "9.9.9")',
        )

    def test_duplicate_metadata_rejected(self):
        self.reject_mutation(
            '    A: platformBuildVersionCode=(type 0x10)0x24',
            '    A: platformBuildVersionCode=(type 0x10)0x24\n'
            '    A: platformBuildVersionCode=(type 0x10)0x24',
        )

    def test_unknown_attribute_rejected(self):
        self.reject_mutation(
            '      A: android:hasCode(0x0101000c)=(type 0x12)0x0',
            '      A: android:enabled(0x0101000e)=(type 0x12)0x1\n'
            '      A: android:hasCode(0x0101000c)=(type 0x12)0x0',
        )

if __name__ == "__main__":
    unittest.main()
