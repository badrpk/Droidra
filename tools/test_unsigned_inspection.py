import io
import sys
import tempfile
import unittest
import zipfile
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch, call

import verify_broker_apk as verifier

from test_verify_broker_apk import GOOD_MANIFEST
from test_realistic_manifest_contract import BASE



class UnsignedInspectionTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

        self.apk = Path(self.temp.name) / "broker.apk"

        with zipfile.ZipFile(self.apk, "w") as archive:
            archive.writestr(
                "AndroidManifest.xml",
                b"compiled-manifest-placeholder",
            )

    def tool_output(self, command):
        if "badging" in command:
            return "package: name='com.sophyane.rsi.broker'"
        if "permissions" in command:
            return "package: com.sophyane.rsi.broker"
        if "xmltree" in command:
            return BASE
        if "verify" in command:
            return "Verified"
        raise AssertionError(f"Unexpected tool call: {command}")

    def test_unsigned_inspection_skips_signature_only(self):
        with patch.object(
            verifier,
            "run",
            side_effect=self.tool_output,
        ) as mocked:
            verifier.verify_apk(
                self.apk,
                "aapt",
                None,
            )

        self.assertEqual(mocked.call_count, 3)
        self.assertFalse(
            any("apksigner" in str(c) for c in mocked.call_args_list)
        )

    def test_signed_verification_still_requires_apksigner(self):
        with patch.object(
            verifier,
            "run",
            side_effect=self.tool_output,
        ) as mocked:
            verifier.verify_apk(
                self.apk,
                "aapt",
                "apksigner",
            )

        self.assertEqual(mocked.call_count, 4)
        self.assertEqual(
            mocked.call_args_list[-1],
            call([
                "apksigner",
                "verify",
                "--verbose",
                "--print-certs",
                str(self.apk),
            ]),
        )

    def test_unsigned_inspection_rejects_permission(self):
        def bad_permission(command):
            if "permissions" in command:
                return (
                    "uses-permission: "
                    "name='android.permission.INTERNET'"
                )
            return self.tool_output(command)

        with patch.object(
            verifier,
            "run",
            side_effect=bad_permission,
        ):
            with self.assertRaises(ValueError):
                verifier.verify_apk(self.apk, "aapt", None)

    def test_unsigned_inspection_rejects_component(self):
        def bad_component(command):
            if "xmltree" in command:
                return BASE + "\n  E: service\n"
            return self.tool_output(command)

        with patch.object(
            verifier,
            "run",
            side_effect=bad_component,
        ):
            with self.assertRaises(ValueError):
                verifier.verify_apk(self.apk, "aapt", None)

    def test_unsigned_inspection_rejects_dex(self):
        with zipfile.ZipFile(self.apk, "a") as archive:
            archive.writestr("classes.dex", b"not-real-dex")

        with patch.object(
            verifier,
            "run",
            side_effect=self.tool_output,
        ):
            with self.assertRaises(ValueError):
                verifier.verify_apk(self.apk, "aapt", None)

    def test_unsigned_cli_dispatch(self):
        argv = [
            "verify_broker_apk.py",
            "--unsigned-inspection",
            str(self.apk),
            "aapt",
        ]

        with (
            patch.object(sys, "argv", argv),
            patch.object(verifier, "verify_apk") as mocked,
            redirect_stdout(io.StringIO()),
        ):
            verifier.main()

        mocked.assert_called_once_with(
            self.apk,
            "aapt",
            None,
        )

    def test_signed_cli_dispatch_preserved(self):
        argv = [
            "verify_broker_apk.py",
            str(self.apk),
            "aapt",
            "apksigner",
        ]

        with (
            patch.object(sys, "argv", argv),
            patch.object(verifier, "verify_apk") as mocked,
            redirect_stdout(io.StringIO()),
        ):
            verifier.main()

        mocked.assert_called_once_with(
            self.apk,
            "aapt",
            "apksigner",
        )

    def test_missing_cli_argument_rejected(self):
        with patch.object(
            sys,
            "argv",
            ["verify_broker_apk.py", "--unsigned-inspection"],
        ):
            with self.assertRaises(SystemExit):
                verifier.main()


if __name__ == "__main__":
    unittest.main()
