from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
import json
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class AndroidApp:
    name: str
    package_id: str
    module_path: str
    min_sdk: int
    target_sdk: int
    version_name: str
    version_code: int
    play_enabled: bool = True

    def validate(self) -> None:
        if not self.name.strip():
            raise ValueError("app name is required")
        if "." not in self.package_id or self.package_id.startswith(".") or self.package_id.endswith("."):
            raise ValueError(f"invalid package_id: {self.package_id}")
        if self.min_sdk < 21:
            raise ValueError("min_sdk must be >= 21")
        if self.target_sdk < self.min_sdk:
            raise ValueError("target_sdk must be >= min_sdk")
        if self.version_code < 1:
            raise ValueError("version_code must be positive")
        if not self.version_name.strip():
            raise ValueError("version_name is required")


class AppRegistry:
    def __init__(self, apps: Iterable[AndroidApp] = ()) -> None:
        self._apps: dict[str, AndroidApp] = {}
        self._packages: set[str] = set()
        for app in apps:
            self.register(app)

    def register(self, app: AndroidApp) -> None:
        app.validate()
        key = app.name.casefold()
        if key in self._apps:
            raise ValueError(f"duplicate app name: {app.name}")
        if app.package_id in self._packages:
            raise ValueError(f"duplicate package_id: {app.package_id}")
        self._apps[key] = app
        self._packages.add(app.package_id)

    def get(self, name: str) -> AndroidApp:
        try:
            return self._apps[name.casefold()]
        except KeyError as exc:
            raise KeyError(f"unknown app: {name}") from exc

    def apps(self) -> list[AndroidApp]:
        return sorted(self._apps.values(), key=lambda app: app.name.casefold())

    def release_manifest(self) -> dict:
        apps = [asdict(app) for app in self.apps()]
        payload = {"schema": 1, "apps": apps}
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return {
            **payload,
            "sha256": sha256(canonical.encode("utf-8")).hexdigest(),
        }

    def validate_checkout(self, root: str | Path) -> list[str]:
        root = Path(root)
        errors: list[str] = []
        for app in self.apps():
            module = root / app.module_path
            if not module.is_dir():
                errors.append(f"missing module: {app.module_path}")
                continue
            if not (module / "build.gradle.kts").exists() and not (module / "build.gradle").exists():
                errors.append(f"missing Gradle file: {app.module_path}")
            if not (module / "src/main/AndroidManifest.xml").exists():
                errors.append(f"missing manifest: {app.module_path}")
            if app.play_enabled and not (module / "play/listing/en-US/title.txt").exists():
                errors.append(f"missing Play listing: {app.module_path}")
        return errors

    def write_manifest(self, path: str | Path) -> None:
        Path(path).write_text(
            json.dumps(self.release_manifest(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def default_registry() -> AppRegistry:
    # The canonical inventory can be extended as more Droidra apps are promoted.
    return AppRegistry(
        [
            AndroidApp(
                name="bijli",
                package_id="com.badrpk.bijli",
                module_path="apps/bijli",
                min_sdk=21,
                target_sdk=35,
                version_name="1.0.0",
                version_code=1,
            ),
            AndroidApp(
                name="cast",
                package_id="com.badrpk.cast",
                module_path="apps/cast",
                min_sdk=21,
                target_sdk=35,
                version_name="1.0.0",
                version_code=1,
            ),
        ]
    )


if __name__ == "__main__":
    registry = default_registry()
    print(json.dumps(registry.release_manifest(), indent=2, sort_keys=True))
