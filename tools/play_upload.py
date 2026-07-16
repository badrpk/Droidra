#!/usr/bin/env python3
"""Upload AABs to Google Play using a service account JSON.

Usage:
  export GOOGLE_APPLICATION_CREDENTIALS=/path/to/play-service-account.json
  python3 tools/play_upload.py --aab-dir ~/play-aabs --track internal

Requires:
  pip install google-api-python-client google-auth
  Play Console → Users and permissions → Invite service account with Release apps
  Link Cloud project + enable Android Publisher API
"""
from __future__ import annotations
import argparse, json, mimetypes, os, sys, time
from pathlib import Path

APPS = {
    "sophyane": "com.badrpk.sophyane",
    "khaana": "com.badrpk.khaana",
    "mypharma": "com.badrpk.mypharma",
    "bijli": "com.badrpk.bijli",
    "laibabadar": "com.badrpk.laibabadar",
    "rangoons": "com.badrpk.rangoons",
    "vps": "com.badrpk.vps",
    "shmry": "com.badrpk.shmry",
    "huobz": "com.badrpk.huobz",
    "nifdu": "com.badrpk.nifdu",
    "darulsakina": "com.badrpk.darulsakina",
    "cast": "com.badrpk.cast",
    "xerus": "com.badrpk.xerus",
}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--aab-dir", default=str(Path.home() / "play-aabs"))
    ap.add_argument("--track", default="internal", choices=["internal", "alpha", "beta", "production"])
    ap.add_argument("--status", default="draft")  # draft | completed
    args = ap.parse_args()

    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or os.environ.get("PLAY_SERVICE_ACCOUNT_JSON")
    if not creds_path or not Path(creds_path).exists():
        print("ERROR: Set GOOGLE_APPLICATION_CREDENTIALS to Play service-account JSON path.")
        print("Create in Google Cloud → IAM → Service account, then invite in Play Console API access.")
        sys.exit(2)

    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
    except ImportError:
        print("pip install google-api-python-client google-auth")
        sys.exit(2)

    scopes = ["https://www.googleapis.com/auth/androidpublisher"]
    creds = service_account.Credentials.from_service_account_file(creds_path, scopes=scopes)
    service = build("androidpublisher", "v3", credentials=creds, cache_discovery=False)

    aab_dir = Path(args.aab_dir)
    results = []
    for name, package in APPS.items():
        aab = aab_dir / f"{name}-release.aab"
        if not aab.exists():
            print("SKIP missing", aab)
            results.append({"app": name, "ok": False, "error": "missing_aab"})
            continue
        try:
            edit = service.edits().insert(body={}, packageName=package).execute()
            edit_id = edit["id"]
            media = MediaFileUpload(str(aab), mimetype="application/octet-stream", resumable=True)
            bundle = service.edits().bundles().upload(
                editId=edit_id, packageName=package, media_body=media
            ).execute()
            version_code = bundle.get("versionCode")
            service.edits().tracks().update(
                editId=edit_id,
                track=args.track,
                packageName=package,
                body={
                    "track": args.track,
                    "releases": [{
                        "name": f"1.0.0 ({version_code})",
                        "versionCodes": [str(version_code)],
                        "status": args.status,
                    }],
                },
            ).execute()
            if args.status == "completed":
                service.edits().commit(editId=edit_id, packageName=package).execute()
            else:
                # keep draft edit committed so it appears in console
                service.edits().commit(editId=edit_id, packageName=package).execute()
            print("OK", package, "v", version_code, "track", args.track)
            results.append({"app": name, "ok": True, "package": package, "versionCode": version_code})
        except Exception as e:
            print("FAIL", package, e)
            results.append({"app": name, "ok": False, "package": package, "error": str(e)})
            time.sleep(1)
    Path("/tmp/play_upload_results.json").write_text(json.dumps(results, indent=2))
    print("wrote /tmp/play_upload_results.json")
    ok = sum(1 for r in results if r.get("ok"))
    print(f"uploaded {ok}/{len(results)}")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
