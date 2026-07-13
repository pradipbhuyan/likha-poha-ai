#!/bin/bash
# ============================================================
# Likha Poha AI — Local Android APK Build Script
# Usage: cd mobile && bash build_apk.sh
# Requires: Android Studio + Node.js installed
# No Zscaler? Just run this script — it works without Zscaler.
# ============================================================

set -e  # Exit on any error

echo "🚀 Likha Poha AI — Building Android APK"
echo "========================================="

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

# ── 3. Generate native Android project ───────────────────────
echo ""
echo "🔨 Generating Android project (expo prebuild)..."
npx expo prebuild --platform android --clean --no-install

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
