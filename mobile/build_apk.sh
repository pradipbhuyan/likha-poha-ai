#!/bin/bash
# ============================================================
# Likha Poha AI — Local Android APK Build Script
# Usage: cd mobile && bash build_apk.sh
# Requires: Android Studio + Node.js installed
# No Zscaler? Just run this script — it works without Zscaler.
# ============================================================

set -e  # Exit on any error

# ── Script version ────────────────────────────────────────────
BUILD_SCRIPT_VERSION="v6.0"
BUILD_SCRIPT_DATE="2026-07-14"
# v1.0 — initial build script
# v2.0 — added git pull (auto-fetch latest code)
# v3.0 — added 14-point feature verification checklist
# v4.0 — added version header + CI fix (vitest env vars)
# v5.0 — rm -rf android/ before prebuild (fixes ENOTEMPTY on second+ builds)
# v5.1 — verify all required assets exist before building
# v6.0 — Metro bundle test (catches missing imports BEFORE 10-min Gradle build)

echo "🚀 Likha Poha AI — Building Android APK"
echo "========================================="
echo "📋 Build script: $BUILD_SCRIPT_VERSION ($BUILD_SCRIPT_DATE)"
echo "   ✅ This is the CORRECT version (has git pull + feature checks)"
echo ""

# ── 0. Pull latest code from git ─────────────────────────────
echo ""
echo "📥 Pulling latest code from GitHub..."
# Go up one level to repo root to pull, then come back
cd ..
git pull
cd mobile
echo "✅ Code: $(git log --oneline -1)"
echo ""

# ── 0b. Verify all required features are present ─────────────
echo "🔍 Verifying feature checklist..."
FAIL=0

check() {
  local desc="$1"
  local file="$2"
  local pattern="$3"
  # Script runs from mobile/ directory
  if grep -q "$pattern" "$file" 2>/dev/null; then
    echo "  ✅ $desc"
  else
    echo "  ❌ MISSING: $desc  ($file)"
    FAIL=1
  fi
}

check "Google OAuth WebView (Zscaler-safe)"  "app/auth/login.tsx"        "NativeWebView"
check "Username login"                        "app/auth/login.tsx"        "lookup-email"
check "Dark mode (useTheme)"                  "app/auth/login.tsx"        "useTheme"
check "Grades 5-12 in signup"                 "app/auth/signup.tsx"       '"11", "12"'
check "Stream selector (PCM/PCB)"             "app/auth/signup.tsx"       "STREAMS"
check "Google OAuth role picker"              "app/auth/role-select.tsx"  "completeOAuthProfile"
check "Grade lock (free tier)"                "app/(tabs)/lessons.tsx"    "isGradeLocked"
check "Exemplar locked banner"                "app/(tabs)/lessons.tsx"    "isExemplarLocked"
check "Exam Prep 3 tabs"                      "app/(tabs)/examprep.tsx"   "Simulated Test"
check "NTA countdown timer"                   "app/(tabs)/examprep.tsx"   "CountdownTimer"
check "Simulated Test submit snake_case"      "app/(tabs)/examprep.tsx"   "time_spent_seconds"
check "SafeAreaProvider at root"              "app/_layout.tsx"           "SafeAreaProvider"
check "expo-router entry point"               "index.ts"                  "expo-router/entry"

# File existence checks (no grep needed)
[ -f "assets/icon-1024.png"       ] && echo "  ✅ App icon 1024px"             || { echo "  ❌ MISSING: assets/icon-1024.png";       FAIL=1; }
[ -f "assets/likhapohaai.gif"     ] && echo "  ✅ Likha Poha AI loading GIF"   || { echo "  ❌ MISSING: assets/likhapohaai.gif";     FAIL=1; }
[ -f "assets/google-logo.png"     ] && echo "  ✅ Google logo"                 || { echo "  ❌ MISSING: assets/google-logo.png";     FAIL=1; }
[ -f "lib/examprep-data.ts"       ] && echo "  ✅ Exam Prep data module"       || { echo "  ❌ MISSING: lib/examprep-data.ts";       FAIL=1; }

if [ $FAIL -ne 0 ]; then
  echo ""
  echo "❌ VERIFICATION FAILED — some features are missing!"
  echo "   Run: git pull  (to make sure you have latest code)"
  echo "   Then retry: bash build_apk.sh"
  exit 1
fi
echo ""
echo "✅ All features verified — proceeding with build"
echo ""

# ── 1. Set environment variables ──────────────────────────────
export JAVA_HOME="/Applications/Android Studio.app/Contents/jbr/Contents/Home"
export ANDROID_HOME="$HOME/Library/Android/sdk"
export PATH="$ANDROID_HOME/platform-tools:$ANDROID_HOME/tools:$PATH"

# Verify Java
if ! "$JAVA_HOME/bin/java" -version 2>/dev/null; then
  echo "❌ Java not found. Install Android Studio from https://developer.android.com/studio"
  exit 1
fi
echo "✅ Java: $("$JAVA_HOME/bin/java" -version 2>&1 | head -1)"

# ── 2. Install JS dependencies ────────────────────────────────
echo ""
echo "📦 Installing dependencies..."
npm install

# ── 2b. Bundle test — verifies all imports resolve (using expo export) ────
echo ""
echo "🔬 Bundle test (checks all imports resolve before 10-min Gradle build)..."
EXPORT_DIR="/tmp/likhapoha-expo-export"
BUNDLE_LOG="/tmp/likhapoha-bundle-log.txt"
rm -rf "$EXPORT_DIR" "$BUNDLE_LOG"

# Use expo export (works on any Expo project without @react-native-community/cli)
set +e
npx expo export --platform android --output-dir "$EXPORT_DIR" > "$BUNDLE_LOG" 2>&1
BUNDLE_EXIT=$?
set -e

if [ $BUNDLE_EXIT -ne 0 ]; then
  echo ""
  echo "❌ Bundle test FAILED — import errors found:"
  grep -E "Unable to resolve|Cannot find|Error:|error " "$BUNDLE_LOG" | head -10 || tail -15 "$BUNDLE_LOG"
  echo ""
  echo "   Common causes: missing assets (gif/png), wrong import paths, missing lib files"
  echo "   Run: git pull && bash build_apk.sh"
  rm -rf "$EXPORT_DIR" "$BUNDLE_LOG"
  exit 1
fi

rm -rf "$EXPORT_DIR" "$BUNDLE_LOG"
echo "✅ Bundle test passed — all modules resolved"
echo ""

# ── 3. Generate native Android project ───────────────────────
echo ""
echo "🔨 Generating Android project (expo prebuild)..."
# Force-remove android/ so expo prebuild --clean doesn't fail with ENOTEMPTY
echo "  Removing old android/ directory..."
rm -rf android
# CI=1 skips the "uncommitted changes" interactive prompt
CI=1 npx expo prebuild --platform android --clean --no-install

# ── 4. Create minimal network_security_config (no Zscaler) ───
echo ""
echo "🔐 Creating network security config..."
mkdir -p android/app/src/main/res/xml

cat > android/app/src/main/res/xml/network_security_config.xml << 'XML'
<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
    <base-config cleartextTrafficPermitted="true">
        <trust-anchors>
            <certificates src="system" />
            <certificates src="user" />
        </trust-anchors>
    </base-config>
    <domain-config cleartextTrafficPermitted="true">
        <domain includeSubdomains="true">192.168.1.5</domain>
        <domain includeSubdomains="true">10.0.2.2</domain>
        <domain includeSubdomains="true">localhost</domain>
    </domain-config>
</network-security-config>
XML

# Apply the manifest reference
sed -i '' 's|android:fullBackupContent|android:networkSecurityConfig="@xml/network_security_config" android:fullBackupContent|' \
  android/app/src/main/AndroidManifest.xml

echo "✅ network_security_config.xml created"

# ── 5. Build release APK ──────────────────────────────────────
echo ""
echo "🏗️  Building release APK (this takes 3–10 min on first run)..."
cd android
./gradlew assembleRelease
cd ..

# ── 6. Done ───────────────────────────────────────────────────
APK_PATH="android/app/build/outputs/apk/release/app-release.apk"
APK_SIZE=$(du -sh "$APK_PATH" | cut -f1)

echo ""
echo "========================================="
echo "✅ BUILD SUCCESSFUL!"
echo "📱 APK: $APK_PATH ($APK_SIZE)"
echo ""
echo "To install on phone via USB:"
echo "  $ANDROID_HOME/platform-tools/adb install $APK_PATH"
echo ""
echo "Or copy $APK_PATH to Google Drive and install from phone."
echo "========================================="

# Open Finder at APK location (macOS only)
open "android/app/build/outputs/apk/release/" 2>/dev/null || true
