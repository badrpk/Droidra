#!/bin/sh
# Minimal gradlew bootstrap — prefer Android Studio Sync or: gradle wrapper
if command -v gradle >/dev/null 2>&1; then
  exec gradle "$@"
fi
echo "Install Android Studio or run: gradle wrapper && ./gradlew $*"
exit 1
