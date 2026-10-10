#!/usr/bin/env python3

import re
import subprocess
import sys
import zipfile
from pathlib import Path

EXPECTED_PACKAGE = "com.sophyane.rsi.broker"

FORBIDDEN_COMPONENTS = {
    "activity",
    "activity-alias",
    "service",
    "receiver",
    "provider",
    "instrumentation",
}

REQUIRED_FALSE = {
    "allowBackup",
    "hasCode",
    "usesCleartextTraffic",
}


def reject(reason):
    raise ValueError(reason)


def run(command):
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def verify_badging(text):
    matches = re.findall(
        r"^package: name='([^']+)'",
        text,
        flags=re.MULTILINE,
    )

    if matches != [EXPECTED_PACKAGE]:
        reject("Unexpected package identity")


def verify_permissions(text):
    if re.search(
        r"uses-permission(?:-sdk-\d+)?:",
        text,
        flags=re.IGNORECASE,
    ):
        reject("Unexpected requested permission")


def verify_manifest(text, *, strict=False):
    if not text.strip():
        reject("Empty compiled manifest")

    element_pattern = re.compile(
        r"^( *)(?:E:)\s*"
        r"([A-Za-z][A-Za-z0-9_-]*)(?:\s|$)"
    )

    typed_attribute = re.compile(
        r"^( *)(?:A:)\s*"
        r"([A-Za-z][A-Za-z0-9_:.-]*)"
        r"\([^)]*\)=\(type 0x([0-9a-fA-F]+)\)"
        r"(0x[0-9a-fA-F]+)\s*$"
    )

    raw_package = re.compile(
        r'^(\s*)A: package="([^"]+)" '
        r'\(Raw: "([^"]+)"\)\s*$'
    )

    namespace_pattern = re.compile(
        r"^N: android="
        r"http://schemas\.android\.com/apk/res/android$"
    )

    stack = []
    root_count = 0
    application_count = 0
    sdk_count = 0
    sdk_attribute_names = set()
    namespace_count = 0
    package_count = 0

    security_resource_ids = {
        "android:allowBackup": "01010280",
        "android:debuggable": "0101000f",
        "android:hasCode": "0101000c",
        "android:usesCleartextTraffic": "010104ec",
        "android:extractNativeLibs": "010104ea",
    }
    application_attributes = {}

    for raw_line in text.splitlines():
        if not raw_line.strip():
            continue

        if namespace_pattern.fullmatch(raw_line):
            if stack or root_count or namespace_count:
                reject("Invalid namespace declaration")
            namespace_count += 1
            continue

        element = element_pattern.fullmatch(raw_line)

        if element:
            indent = len(element.group(1))
            name = element.group(2)

            while stack and stack[-1][0] >= indent:
                stack.pop()

            parent = stack[-1][1] if stack else None

            if name == "manifest":
                if parent is not None or root_count:
                    reject("Invalid manifest root")
                root_count += 1

            elif name == "application":
                if parent != "manifest" or application_count:
                    reject("Invalid application placement")
                application_count += 1

            elif name == "uses-sdk":
                if parent != "manifest" or sdk_count:
                    reject("Invalid uses-sdk placement")
                sdk_count += 1

            else:
                reject(f"Unexpected manifest element: {name}")

            stack.append((indent, name, set()))
            continue

        package = raw_package.fullmatch(raw_line)

        if package:
            indent = len(package.group(1))

            if (
                not stack
                or stack[-1][1] != "manifest"
                or indent <= stack[-1][0]
                or package_count
            ):
                reject("Invalid package attribute")

            if (
                package.group(2) != EXPECTED_PACKAGE
                or package.group(3) != EXPECTED_PACKAGE
            ):
                reject("Unexpected manifest package")

            if "package" in stack[-1][2]:
                reject("Duplicate attribute: package")

            stack[-1][2].add("package")
            package_count += 1
            continue

        if stack and stack[-1][1] == "manifest":
            match = re.fullmatch(
                r'^( *)A: (android:versionName|android:compileSdkVersionCodename)'
                r'\(0x([0-9a-fA-F]+)\)="([^"]+)" \(Raw: "([^"]+)"\)\s*',
                raw_line,
            )
            if match:
                expected = {
                    "android:versionName": ("0101021c", "0.1.0"),
                    "android:compileSdkVersionCodename": ("01010573", "16"),
                }[match.group(2)]
                if (
                    len(match.group(1)) <= stack[-1][0]
                    or match.group(3).lower() != expected[0]
                    or match.group(4) != expected[1]
                    or match.group(5) != expected[1]
                    or match.group(2) in stack[-1][2]
                ):
                    reject("Invalid manifest string metadata")
                stack[-1][2].add(match.group(2))
                continue

        attribute = typed_attribute.fullmatch(raw_line)

        if attribute:
            indent = len(attribute.group(1))
            name = attribute.group(2)
            value_type = attribute.group(3).lower()
            value = attribute.group(4).lower()

            resource_id_match = re.search(
                r"\(0x([0-9a-fA-F]+)\)=",
                raw_line,
            )
            if resource_id_match is None and name not in {
                "platformBuildVersionCode", "platformBuildVersionName"
            }:
                reject("Missing attribute resource ID")

            resource_id = resource_id_match.group(1).lower() if resource_id_match else None

            if not stack or indent <= stack[-1][0]:
                reject("Attribute outside element")

            element_name = stack[-1][1]
            seen = stack[-1][2]

            if name in seen:
                reject(f"Duplicate attribute: {name}")

            seen.add(name)

            if name == "package":
                reject("Unexpected typed package attribute")
            if element_name == "manifest":
                metadata = {
                    "android:versionCode": ("0101021b", "10", 1),
                    "android:compileSdkVersion": ("01010572", "10", 36),
                    "platformBuildVersionCode": (None, "10", 36),
                    "platformBuildVersionName": (None, "10", 16),
                }
                expected = metadata.get(name)
                if expected is None or (resource_id, value_type, int(value, 16)) != expected:
                    reject("Unexpected manifest build metadata")
                continue

            expected_resource_id = security_resource_ids.get(name)

            if (
                expected_resource_id is not None
                and resource_id != expected_resource_id
            ):
                reject(
                    f"Incorrect security resource ID: {name}"
                )

            if element_name == "uses-sdk":
                if name not in {
                    "android:minSdkVersion",
                    "android:targetSdkVersion",
                }:
                    reject("Unexpected uses-sdk attribute")

                expected = {
                    "android:minSdkVersion": "0x1a",
                    "android:targetSdkVersion": "0x24",
                }[name]

                if value_type != "10" or int(value, 16) != int(
                    expected, 16
                ):
                    reject("Unexpected SDK version")

                sdk_attribute_names.add(name)

            elif element_name == "application":
                allowed_application_attributes = {
                    "android:allowBackup",
                    "android:debuggable",
                    "android:hasCode",
                    "android:usesCleartextTraffic",
                    "android:extractNativeLibs",
                }

                if name not in allowed_application_attributes:
                    reject(
                        f"Unexpected application attribute: {name}"
                    )

                application_attributes[name] = (
                    value_type, value
                )

            elif element_name == "manifest":
                reject(f"Unexpected manifest attribute: {name}")

            else:
                reject(
                    f"Unexpected attribute placement: {name}"
                )

            continue

        reject("Unexpected manifest output")

    if root_count != 1 or application_count != 1:
        reject("Missing manifest or application")

    if strict and (namespace_count != 1 or package_count != 1):
        reject("Missing required namespace or package identity")

    if sdk_count:
        sdk_attributes = sdk_attribute_names

        if sdk_attributes != {
            "android:minSdkVersion",
            "android:targetSdkVersion",
        }:
            reject("Missing required SDK version attribute")

    if application_attributes.get("android:debuggable", ("12", "0x0")) != ("12", "0x0"):
        reject("Debuggable enabled or invalid")
    if application_attributes.get("android:extractNativeLibs", ("12", "0x0")) != ("12", "0x0"):
        reject("Native library extraction enabled or invalid")

    for attribute in REQUIRED_FALSE:
        key = f"android:{attribute}"

        if application_attributes.get(key) != (
            "12", "0x0"
        ):
            reject(
                f"Required false attribute invalid: {key}"
            )

def verify_archive(path):
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()

    for name in names:
        if re.fullmatch(r"classes\d*\.dex", name):
            reject("Unexpected DEX file")


def verify_apk(apk, aapt, apksigner):
    verify_badging(
        run([aapt, "dump", "badging", str(apk)])
    )

    verify_permissions(
        run([aapt, "dump", "permissions", str(apk)])
    )

    verify_manifest(
        run([
            aapt,
            "dump",
            "xmltree",
            str(apk),
            "AndroidManifest.xml",
        ])
    , strict=True)

    verify_archive(apk)

    if apksigner is not None:
        run([
            apksigner,
        "verify",
        "--verbose",
        "--print-certs",
        str(apk),
        ])


def main():
    if len(sys.argv) == 4 and sys.argv[1] == "--unsigned-inspection":
        apk = Path(sys.argv[2])
        aapt = sys.argv[3]
        apksigner = None
    elif len(sys.argv) == 4 and not sys.argv[1].startswith("-"):
        apk = Path(sys.argv[1])
        aapt = sys.argv[2]
        apksigner = sys.argv[3]
    else:
        raise SystemExit(
            "Usage: verify_broker_apk.py APK AAPT APKSIGNER "
            "| --unsigned-inspection APK AAPT"
        )

    if not apk.is_file():
        reject("APK not found")

    verify_apk(apk, aapt, apksigner)

    if apksigner is None:
        print("BROKER_UNSIGNED_INSPECTION=PASS")
    else:
        print("BROKER_COMPILED_APK=PASS")


if __name__ == "__main__":
    try:
        main()
    except (
        ValueError,
        OSError,
        subprocess.CalledProcessError,
        zipfile.BadZipFile,
    ) as exc:
        print(f"BROKER_COMPILED_APK=FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
