# Likha Poha AI — Mobile App

_Last updated: 2026-07-12_
_Status: **Working via Expo Go. Standalone APK being validated (Build #18).**_

---

## Working SDK Stack (as of 2026-07-12)

| Package | Version | Notes |
|---|---|---|
| `expo` | `~54.0.0` (54.0.35) | Must match Play Store Expo Go in India |
| `expo-router` | `~6.0.24` | SDK 54 needs v6, NOT v4 |
| `react` | `19.1.0` | SDK 54 uses React 19 |
| `react-native` | `0.81.5` | Set via `npx expo install react-native` |
| `expo-secure-store` | `~15.0.8` | Session storage for Supabase |
| `newArchEnabled` | `true` | RN 0.81.5 requires New Architecture |

**Critical rule:** Always use `npx expo install <package>` for Expo packages — NOT `npm install`. This auto-selects the version for the installed SDK.

---

## How to Run (Development)

### Prerequisites
- Expo Go app installed from Play Store (India: SDK 54)
- Mac on same WiFi as Android phone
- Backend running

### Start dev server

```bash
cd /Users/a0247716/Pradips_Project/cbse-tutor-platform/mobile
export PATH=~/.npm-global/bin:$PATH
NODE_TLS_REJECT_UNAUTHORIZED=0 npx expo start --lan --clear
```

### Connect from phone

In Expo Go → "Enter URL manually" → `exp://192.168.1.5:8081`

### Start backend (needed for API calls)

```bash
cd /Users/a0247716/Pradips_Project/cbse-tutor-platform/backend
.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## Building Standalone APK

```bash
cd mobile
export PATH=~/.npm-global/bin:$PATH
NODE_TLS_REJECT_UNAUTHORIZED=0 eas build --platform android --profile preview --non-interactive
```

Track builds at: https://expo.dev/accounts/pradipbhuyans-team/projects/likhapohaai/builds

**Latest build:** `5d57730c` (Build #18, versionCode 13, newArchEnabled:true)

### After build completes

1. Open build URL on Android phone → tap Install
2. Uninstall old version first if upgrading (prevents signing conflicts)
3. Enable "Install from unknown sources" on first install

---

## Project Structure

```
mobile/
├── app/
│   ├── _layout.tsx            ← Root layout — Expo Router entry, Supabase session guard
│   ├── auth/
│   │   ├── _layout.tsx        ← Auth stack layout
│   │   ├── login.tsx          ← Email/password login with Likha Poha logo
│   │   └── signup.tsx         ← Student/parent registration with grade selector
│   └── (tabs)/
│       ├── _layout.tsx        ← Tab bar with Likha Poha logo in header
│       ├── index.tsx          ← Home / Student Dashboard
│       ├── lessons.tsx        ← AI lesson generation (core feature)
│       ├── mocktest.tsx       ← Mock tests
│       └── account.tsx        ← User profile
├── assets/
│   ├── icon.png               ← Likha Poha AI logo (from frontend/public/android-chrome-512x512.png)
│   ├── splash-icon.png        ← Same as icon.png
│   ├── android-icon-foreground.png   ← Adaptive icon foreground
│   └── android-icon-background.png  ← Adaptive icon background
├── constants/
│   └── index.ts               ← BRAND_COLOR, API_BASE_URL, SUPABASE_URL, etc.
├── lib/
│   ├── supabase.ts            ← Supabase client with expo-secure-store adapter
│   ├── auth.ts                ← signInWithEmail, signOut, signUpWithEmail
│   └── authFetch.ts           ← Authenticated fetch with JWT, same 401/403 handling as web
├── .env                       ← EXPO_PUBLIC_* vars (NOT excluded from EAS — required for build)
├── .easignore                 ← Excludes node_modules, build artifacts (NOT .env)
├── app.json                   ← Expo config: SDK 54, newArchEnabled:true, package in.likhapoha.app
├── eas.json                   ← EAS Build profiles (preview = APK, production = AAB)
├── index.ts                   ← Entry point: import "expo-router/entry"
├── MinimalApp.tsx             ← Diagnostic component (used during debugging — can be deleted)
└── tsconfig.json              ← Extends expo/tsconfig.base, jsx:react-native
```

---

## Key Architecture Decisions

### Entry point: `import "expo-router/entry"`

`index.ts` must be exactly:
```ts
import "expo-router/entry";
```

**Never use** `registerRootComponent(App)` — this bypasses Expo Router and causes silent crashes.

### Supabase Storage Adapter

```ts
const ExpoSecureStoreAdapter = {
  getItem: (key) => SecureStore.getItemAsync(key),
  setItem: (key, value) => SecureStore.setItemAsync(key, value),
  removeItem: (key) => SecureStore.deleteItemAsync(key),
};
```

### Navigation Guard in `_layout.tsx`

```tsx
// Slot-based routing — no Stack at root level
// Session guard redirects:
//   logged in + in auth/ → /(tabs)
//   logged out + not in auth/ → /auth/login
```

### authFetch

All API calls use `authFetch()` from `lib/authFetch.ts`:
- Auto-adds `Authorization: Bearer <supabase_jwt>` header
- Throws on 401/403 with meaningful error
- Uses `EXPO_PUBLIC_API_BASE_URL` (local IP for dev, prod URL for production)

---

## Environment Variables

`mobile/.env` (committed, NOT excluded from EAS archive):

```env
EXPO_PUBLIC_API_BASE_URL=http://192.168.1.5:8000   # Mac's local IP
EXPO_PUBLIC_SUPABASE_URL=https://dpivlbbyzlbpwnwgajso.supabase.co
EXPO_PUBLIC_SUPABASE_ANON_KEY=eyJ...
EXPO_PUBLIC_RAZORPAY_KEY_ID=rzp_test_placeholder
```

**Important:** `.env` must NOT be in `.easignore`. EAS reads it at build time to embed `EXPO_PUBLIC_*` values in the JS bundle. If excluded, all values are empty strings and Supabase crashes.

For production APK: Change `EXPO_PUBLIC_API_BASE_URL` to the production backend URL (`https://api.likhapoha.in` or similar) before building.

---

## EAS Build Gotchas

### Archive size

EAS archives from the **repo root** (where `.git` is), NOT from `mobile/`. The `.easignore` must be at the repo root. We have:
- `/.easignore` — repo root (excludes `mobile/node_modules/`, `frontend/`, `backend/`, docs, etc.)
- `/mobile/.easignore` — mobile-level (excludes `node_modules/`, `.expo/`, build artifacts)

### SSL certificate error on Mac

EAS CLI requires internet but this Mac has SSL cert issues. Use:
```bash
NODE_TLS_REJECT_UNAUTHORIZED=0 eas build ...
```

### New Architecture

`newArchEnabled: true` is REQUIRED for React Native 0.81.5 standalone APK. Setting it to `false` causes silent crashes on OxygenOS 16. Expo Go always runs with New Architecture, so code tested in Expo Go is confirmed compatible.

---

## Test Accounts

| Email | Role | Notes |
|---|---|---|
| `admin@tutor.com` | Admin | Full access, no student dashboard data in mobile |
| `likhapohaai@gmail.com` | New student | Created 2026-07-12, email confirmed manually |
| `marketing.student@likhapoha.in` | Student | Pre-seeded with lesson history |
| `vijay.sim.student@example.test` | Student | Pre-seeded |

**New accounts:** After signup, Supabase sends confirmation email. Until confirmed, login fails with "invalid credentials". To bypass for testing, use Supabase admin API:
```bash
curl -X PUT "https://dpivlbbyzlbpwnwgajso.supabase.co/auth/v1/admin/users/<UUID>" \
  -H "Authorization: Bearer <SERVICE_ROLE_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"email_confirm": true}'
```

---

## Mobile vs Web Feature Status

| Feature | Web | Mobile | Notes |
|---|---|---|---|
| Email/password auth | ✅ | ✅ | Supabase |
| Student signup | ✅ | ✅ | Grade selector in signup |
| AI lesson generation | ✅ | ✅ | Same backend endpoints |
| Mock tests | ✅ | ✅ | Same backend |
| Student dashboard | ✅ | ⚠️ | Needs student profile in backend DB |
| Progress tracking | ✅ | ⚠️ | Needs student profile |
| Doubt solving | ✅ | 🔲 | Not yet implemented on mobile |
| Analytics | ✅ | 🔲 | Not yet |
| Push notifications | 🔲 | 🔲 | Planned |
| Google OAuth | ✅ | 🔲 | Needs expo-auth-session deep links |
| Admin console | ✅ | ❌ | Web-only by design |

---

## Commits Made (2026-07-12)

| Commit | What |
|---|---|
| `906ecb6` | Fix entry: `index.ts → expo-router/entry` |
| `d215b06` | Install `punycode` for markdown-it |
| `3e44ab9` | Remove typedRoutes, simplify `_layout.tsx` |
| `40d6e27` | Include `.env` in EAS archive |
| `944d60a` | Downgrade to SDK 52 (then 54) |
| `9a201bf` | Upgrade to correct SDK 54 |
| `593c11c` | Fix react-native to 0.81.5 |
| `70fd904` | Use expo-managed versions (expo-router 6.x) |
| `9039211` | Enable `newArchEnabled: true` |
| `f1c2433` | Replace Expo default icon with real Likha Poha AI logo |
| `29517dd` | Home tab welcome screen for new students |
