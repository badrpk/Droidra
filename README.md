# badrpk Android Apps (all products)

Native **Kotlin + Jetpack Compose** Android clients for every badrpk product, including **Sophyane**.

## Apps

| Module | Package | Product |
|--------|---------|---------|
| `:apps:sophyane` | `com.badrpk.sophyane` | Sophyane |
| `:apps:khaana` | `com.badrpk.khaana` | Khaana |
| `:apps:mypharma` | `com.badrpk.mypharma` | MyPharma |
| `:apps:bijli` | `com.badrpk.bijli` | Bijli |
| `:apps:laibabadar` | `com.badrpk.laibabadar` | Laiba Badar |
| `:apps:rangoons` | `com.badrpk.rangoons` | Rangoons |
| `:apps:vps` | `com.badrpk.vps` | VPS-PK |
| `:apps:shmry` | `com.badrpk.shmry` | SHMRY |
| `:apps:huobz` | `com.badrpk.huobz` | Huobz |
| `:apps:nifdu` | `com.badrpk.nifdu` | NIFDU News |
| `:apps:darulsakina` | `com.badrpk.darulsakina` | Darul Sakina |
| `:apps:cast` | `com.badrpk.cast` | Cast |
| `:apps:xerus` | `com.badrpk.xerus` | Xerus |

## Auth (all apps)

- Sign up / Sign in
- OTP **only** for new/unverified accounts
- **Existing verified users skip OTP**
- Google/Gmail & Facebook login **without OTP**

## GCP API key

1. Copy `local.properties.example` → `local.properties`
2. Set your key (from the email you created / Google Cloud Console):

```properties
GCP_API_KEY=your_key_here
GOOGLE_API_KEY=your_key_here
MAPS_API_KEY=your_key_here
sdk.dir=/path/to/Android/Sdk
```

The key is injected into `BuildConfig` and sent as `X-GCP-API-Key` / `X-Goog-Api-Key` on API calls. **Never commit** `local.properties`.

## Build

```bash
# Requires Android Studio Hedgehog+ or SDK 34 + JDK 17
./gradlew :apps:sophyane:assembleDebug
./gradlew :apps:khaana:assembleRelease
# all release AABs
./gradlew bundleRelease
```

Emulator → backend on host: default API host `10.0.2.2` (see each app `API_BASE`).

## Play Store

See [PLAY_STORE.md](PLAY_STORE.md). Each app has listing text under `apps/<id>/play/listing/`.

## GitHub

Canonical monorepo for all Android clients. Product repos may link here from `apps/android/README.md`.
