# Google Play publishing guide

## What is automated in this repo

- Complete Android app sources for all 13 products
- Release signing config (when `secrets/release.keystore` present)
- Store listing copy per app under `apps/*/play/listing/`
- GitHub Actions workflow to build **AAB** artifacts

## What requires your Play Console (manual / one-time)

Publishing cannot complete without a **Google Play Developer** account linked to `badrpk@gmail.com`:

1. Open https://play.google.com/console and pay the one-time registration if not done
2. Create one app per product (package `com.badrpk.<id>`)
3. Upload the AAB from Actions artifacts or local `./gradlew :apps:<id>:bundleRelease`
4. Complete Data safety, content rating, screenshots, privacy policy URL
5. Submit for review

### Optional API upload (service account)

1. Play Console → Setup → API access → link Cloud project
2. Create service account with **Release to production** permission
3. Download JSON → repo secret `PLAY_SERVICE_ACCOUNT_JSON` (never commit)
4. Uncomment play publisher steps in `.github/workflows/android-release.yml`

## Signing

Generate a release keystore once:

```bash
keytool -genkey -v -keystore secrets/release.keystore -alias badrpk \
  -keyalg RSA -keysize 2048 -validity 10000
```

Set CI secrets: `KEYSTORE_PASSWORD`, `KEY_ALIAS`, `KEY_PASSWORD`, and base64 of the keystore file.

## Packages reserved

| App | applicationId |
|-----|----------------|
| Sophyane | `com.badrpk.sophyane` |
| Khaana | `com.badrpk.khaana` |
| MyPharma | `com.badrpk.mypharma` |
| Bijli | `com.badrpk.bijli` |
| Laiba Badar | `com.badrpk.laibabadar` |
| Rangoons | `com.badrpk.rangoons` |
| VPS-PK | `com.badrpk.vps` |
| SHMRY | `com.badrpk.shmry` |
| Huobz | `com.badrpk.huobz` |
| NIFDU News | `com.badrpk.nifdu` |
| Darul Sakina | `com.badrpk.darulsakina` |
| Cast | `com.badrpk.cast` |
| Xerus | `com.badrpk.xerus` |

## Note on this environment

This build host may not include Android SDK / JDK. Apps are **source-complete** on GitHub; build on Android Studio or GitHub Actions runners (`macos-latest` / `ubuntu-latest` with Android SDK).
