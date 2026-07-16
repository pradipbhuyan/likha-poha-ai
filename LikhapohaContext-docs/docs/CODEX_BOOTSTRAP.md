# Codex Bootstrap

Codex and other AI coding agents must read this file before changing the repository.

## Quickstart

**For any task, start by reading `docs/CODEX_CONTEXT.md`** — it is a single file that contains all the critical context needed: product overview, subscription rules, feature authorization, security rules, canonical service map, and what NOT to do.

After reading `CODEX_CONTEXT.md`, read the role-specific docs below as needed.

## Required Reading

For every meaningful change, read:

- `docs/CODEX_CONTEXT.md` ← **START HERE** (single context file for agents)
- `docs/01_PRODUCT_CONTEXT.md`
- `docs/02_ARCHITECTURE.md`
- `docs/03_SUBSCRIPTIONS.md`
- `docs/FEATURE_MATRIX.md`
- `docs/10_SECURITY.md`
- `docs/12_TESTING.md`
- `docs/13_DEVELOPMENT_GUIDE.md`

For role-specific changes also read:

- Admin: `docs/05_ADMIN_PLATFORM.md`
- Teacher: `docs/06_TEACHER_PLATFORM.md`
- Parent: `docs/07_PARENT_PLATFORM.md`
- Student: `docs/08_STUDENT_PLATFORM.md`
- AI/content: `docs/09_AI_PLATFORM.md`

## Non-Negotiable Rules

1. Do not duplicate subscription or access logic.
2. Use the canonical subscription resolver and feature authorization rules.
3. Backend enforces authorization. Frontend restrictions are never sufficient.
4. Free Tier users must never access premium-only features through UI, direct URL, or direct API.
5. Do not expose secrets, tokens, service-role keys, JWTs, passwords, temporary passwords, Razorpay secrets, or raw webhook payloads.
6. Keep payments and webhooks idempotent.
7. Keep admin-only endpoints server-side protected.
8. Audit sensitive actions and sanitize metadata.
9. Keep migrations idempotent and additive unless explicitly approved.
10. Add or update tests for behavior changes.
11. Update docs when product rules, API contracts, permissions, or architecture change.

## Mobile App Rules (expo-router / React Native)

- **Never place data-only `.ts` files in `mobile/app/`** — expo-router treats every file there as a potential route.
- **Never combine `href: null` with `tabBarButton`** in a `Tabs.Screen options` block — use `href: null` alone to suppress a screen from the tab bar.
- **Never pass raw markdown to `<Markdown>`** — always use `<MathAwareMarkdown>` so LaTeX is converted to Unicode before rendering.
- **Google OAuth on mobile** uses `signInWithGoogle()` in `mobile/lib/auth.ts` which calls `supabase.auth.signInWithOAuth({ skipBrowserRedirect: true })` and returns `{url, redirectUri}`. The login screen opens an in-app WebView (`react-native-webview`) or `WebBrowser.openAuthSessionAsync` — never use `supabase.auth.signInWithOAuth` directly (requires browser redirect, breaks native app).
- **`mobile/lib/`** is for shared utilities and data modules. **`mobile/app/`** is exclusively for expo-router screens and layouts.
- **Username login on mobile**: if input has no `@`, call `GET /api/auth/lookup-email/{username}` to resolve to email before calling `supabase.auth.signInWithPassword`.
- **Grade lock**: `isGradeLocked = studentGrade !== null && !hasFullAccess`. Premium/admin users (`hasFullAccess=true`) see all grades. Free users are locked to enrolled grade.
- **Feature gating**: always fetch from `GET /api/subscription/features` — never infer from `subscription_plan` string. Use `hasFullAccess` for grade lock, `features.EXEMPLAR.allowed` for Exemplar access.
- **Simulated Test submit body**: snake_case — `question_id`, `selected_option`, `time_spent_seconds`. The `startSimulatedTest` API returns `question_ids` (UUIDs only), NOT full question objects — always fetch questions separately per subject after start.
- **Build APK**: use `mobile/build_apk.sh` v7.0+ — auto git pull, 17-point feature verification, `rm -rf android` before prebuild. Never build without running this script.
- **`mobile/index.ts`** must contain only `import "expo-router/entry"` — never replace with `registerRootComponent`.
- **`mobile/.env` EXPO_PUBLIC_API_BASE_URL must use `http://` not `https://`** for local development. Using `https://` against a local IP (no SSL cert) causes `TypeError: Network request failed` on Android for ALL API calls. The backend runs plain HTTP on port 8000.
- **Backend `.env` must be copied manually** to any new machine — it is gitignored. Contains Supabase service role key, LLM API keys, etc.
- **APK env vars are baked at build time** — changing `mobile/.env` only takes effect on the NEXT `bash build_apk.sh`. Changing `.env` without rebuilding has no effect on the installed APK.
- **Verify baked URL** before troubleshooting: `grep -ao "192.168.[^\"' ]*" android/app/build/generated/assets/createBundleReleaseJsAndAssets/index.android.bundle | head -3`
- **Zscaler corporate SSL on Android emulator**: The `build_apk.sh` script (v7.0+) auto-embeds the Zscaler Root CA cert directly into the APK via `network_security_config.xml` (`<certificates src="@raw/zscaler_root_ca" />`). It exports the cert from macOS System Keychain at build time — no manual cert installation on the emulator ever needed. This mirrors the `truststore` approach used in the Python backend. If a new build shows "Network request failed" on corporate WiFi, re-run `bash build_apk.sh` from this machine (the one with Zscaler installed) to embed the cert.
- **Never use `killall -9` on Android emulator processes** — force-kill prevents the emulator from saving its AVD snapshot state (including installed certs, app data). Instead, use `adb emu kill` for graceful shutdown, or close via Android Studio Device Manager. A `killall -9` followed by restart will cold-boot the emulator and lose all saved state.
- **Android emulator install workflow** (emulator already running): `adb install -r app-release.apk && adb shell am force-stop in.likhapoha.app && adb shell am start -n in.likhapoha.app/.MainActivity`. The `app-release.apk` symlink always points to the latest build. Never need to restart the emulator between installs.
- **Expo Go on Zscaler corporate network**: `npx expo start --offline` is required on this machine. Without `--offline`, Expo CLI tries to fetch `api.expo.dev` for dependency validation which Zscaler blocks. Expo Go APK itself cannot be downloaded from GitHub/CDN on Zscaler. Use `npx expo run:android` (builds a dev client locally) or the release APK for testing.
- **`Application.nativeBuildVersion` in Expo Go** returns Expo Go's own Android versionCode (e.g. 13), NOT your app's build number. Use `Constants.appOwnership === "expo"` to detect Expo Go mode and show "Expo Go" instead of a misleading build number. In release APK, `nativeBuildVersion` correctly returns the APK's versionCode.
- **Google OAuth after sign-in**: `handleOAuthSuccess` in `mobile/app/auth/login.tsx` has a double-call guard (`oauthExchangeInProgress ref`) to prevent both `onNavigationStateChange` and `onShouldStartLoadWithRequest` from triggering `exchangeCodeForSession` twice. After successful exchange, `router.replace("/(tabs)")` is called immediately — do NOT rely on `onAuthStateChange` timing for post-OAuth routing on mobile.
- **Dynamic app version**: `account.tsx` reads version from `Constants.expoConfig?.version` (from `app.json`) and build number from `Application.nativeBuildVersion`. The `build_apk.sh` script auto-increments `versionCode` on each build. App version string: `Likha Poha AI v{version} ({os} {Expo Go|build N})`.

## Implementation Style

- Prefer small additive changes.
- Preserve legacy compatibility unless explicitly instructed otherwise.
- Ask targeted questions before changing data model or business rules.
- Keep mobile-first UX.
- Avoid making large monolithic files larger; extract components/services.
- Return safe, structured error states instead of raw backend errors.

## Definition of Done

A change is done only when:

- Backend behavior is correct and authorized.
- Frontend renders correct states on desktop and mobile.
- Relevant regression tests are added.
- Existing tests pass.
- Sensitive data is not exposed.
- Audit/metrics/timeline behavior is updated where applicable.
- Documentation is updated if rules changed.
