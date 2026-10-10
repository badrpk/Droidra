import unittest

from verify_broker_apk import verify_manifest


BASE = """\
N: android=http://schemas.android.com/apk/res/android
  E: manifest
    A: package="com.sophyane.rsi.broker" (Raw: "com.sophyane.rsi.broker")
    E: application
      A: android:allowBackup(0x01010280)=(type 0x12)0x0
      A: android:debuggable(0x0101000f)=(type 0x12)0x0
      A: android:hasCode(0x0101000c)=(type 0x12)0x0
      A: android:usesCleartextTraffic(0x010104ec)=(type 0x12)0x0
"""

WITH_SDK = """\
N: android=http://schemas.android.com/apk/res/android
  E: manifest
    A: package="com.sophyane.rsi.broker" (Raw: "com.sophyane.rsi.broker")
    E: uses-sdk
      A: android:minSdkVersion(0x0101020c)=(type 0x10)0x1a
      A: android:targetSdkVersion(0x01010270)=(type 0x10)0x24
    E: application
      A: android:allowBackup(0x01010280)=(type 0x12)0x0
      A: android:debuggable(0x0101000f)=(type 0x12)0x0
      A: android:hasCode(0x0101000c)=(type 0x12)0x0
      A: android:usesCleartextTraffic(0x010104ec)=(type 0x12)0x0
"""

WITH_FORBIDDEN_PERMISSION = """\
N: android=http://schemas.android.com/apk/res/android
  E: manifest
    A: package="com.sophyane.rsi.broker" (Raw: "com.sophyane.rsi.broker")
    E: uses-permission
      A: android:name(0x01010003)="android.permission.INTERNET" (Raw: "android.permission.INTERNET")
    E: application
      A: android:allowBackup(0x01010280)=(type 0x12)0x0
      A: android:debuggable(0x0101000f)=(type 0x12)0x0
      A: android:hasCode(0x0101000c)=(type 0x12)0x0
      A: android:usesCleartextTraffic(0x010104ec)=(type 0x12)0x0
"""


class RealisticManifestContract(unittest.TestCase):

    def test_namespace_and_raw_package_are_accepted(self):
        verify_manifest(BASE)

    def test_uses_sdk_is_accepted(self):
        verify_manifest(WITH_SDK)

    def test_permission_is_rejected(self):
        with self.assertRaises(ValueError):
            verify_manifest(WITH_FORBIDDEN_PERMISSION)


    def test_forged_package_identity_is_rejected(self):
        forged = BASE.replace(
            'package="com.sophyane.rsi.broker"',
            'package="com.attacker.broker"',
        )
        with self.assertRaises(ValueError):
            verify_manifest(forged)



if __name__ == "__main__":
    unittest.main()
