# Likha Poha AI — Mobile App Strategy & Play Store Guide

_Created: 2026-07-12_  
_Platform target: Android (Google Play Store first; iOS later)_  
_Approach: React Native + Expo, monorepo with shared JS layer_

---

## Core Principle: Web Version Must Never Break

Every decision in this document is made with one hard constraint:

> **`frontend/` is read-only during mobile development.**  
> Nothing in `frontend/src/` is touched, deleted, or renamed.  
> The existing web CI (vitest + eslint) must pass at every commit.

Shared fixes (bug fixes in `normalizeTutorMarkdown`, subscription logic, API clients) are extracted to a `shared/` package that **both** web and mobile import. The fix is written once and applies to both.

---

## Monorepo Structure (Target)

```
cbse-tutor-platform/              ← repo root
├── backend/                      ← FastAPI (UNCHANGED — serves both web and mobile)
├── frontend/                     ← React/Vite web app (DO NOT TOUCH during mobile work)
│
├── shared/                       ← NEW: pure-JS code shared by web + mobile
│   ├── api/                      ← API clients (moved from frontend/src/api/)
│   │   ├── auth.js
│   │   ├── lesson.js
│   │   ├── doubt.js
│   │   ├── mockTest.js
│   │   ├── analytics.js
│   │   ├── progress.js
│   │   ├── syllabus.js
│   │   └── tts.js
│   ├── utils/
│   │   ├── markdownCleanup.js    ← normalizeTutorMarkdown pipeline
│   │   ├── resolveSubscription.js
│   │   ├── subjectAccess.js
│   │   └── syllabusDefaults.js
│   ├── config/
│   │   └── subscriptionPlans.js
│   └── package.json              ← name: "@likhapoha/shared", version: "1.0.0"
│
├── mobile/                       ← NEW: React Native / Expo app
│   ├── app/                      ← Expo Router screens
│   │   ├── (tabs)/
│   │   │   ├── index.tsx         ← Student Dashboard
│   │   │   ├── lessons.tsx
│   │   │   ├── mocktest.tsx
│   │   │   └── account.tsx
│   │   ├── login.tsx
│   │   ├── signup.tsx
│   │   └── _layout.tsx
│   ├── components/               ← Mobile-specific UI components
│   │   ├── MathText.tsx          ← LaTeX rendering via react-native-math-view
│   │   ├── LessonCard.tsx
│   │   └── MarkdownLesson.tsx
│   ├── hooks/                    ← Mobile-specific hooks
│   ├── constants/
│   ├── assets/                   ← App icon, splash screen
│   ├── app.json                  ← Expo config (Android bundle ID, version, etc.)
│   ├── eas.json                  ← EAS Build profiles
│   └── package.json
│
├── LikhapohaContext-docs/        ← Platform docs (this file lives here)
└── package.json                  ← Workspace root: ["frontend","mobile","shared"]
```

---

## How Shared Fixes Work (Web + Mobile Stay In Sync)

### Example: `normalizeTutorMarkdown` fix

**Before (separate copies, drift risk):**
```
frontend/src/utils/markdownCleanup.js   ← web version
mobile/utils/markdownCleanup.js         ← mobile copy (gets out of date)
```

**After (single shared source):**
```
shared/utils/markdownCleanup.js         ← ONE copy, fixed once, used by both

frontend/src/utils/markdownCleanup.js   ← re-exports from "@likhapoha/shared"
mobile/utils/markdownCleanup.js         ← re-exports from "@likhapoha/shared"
```

```js
// frontend/src/utils/markdownCleanup.js (after migration)
export * from "@likhapoha/shared/utils/markdownCleanup";
```

```js
// mobile/utils/markdownCleanup.js
export * from "@likhapoha/shared/utils/markdownCleanup";
```

When a bug is fixed in `normalizeTutorMarkdown`, one file changes, both platforms get the fix, CI runs on both, one commit merges to main.

---

## Phase 1: Monorepo Setup (Do This First — No Mobile Code Yet)

### Step 1.1 — Create `shared/` package

```bash
mkdir -p /Users/a0247716/Pradips_Project/cbse-tutor-platform/shared/api
mkdir -p /Users/a0247716/Pradips_Project/cbse-tutor-platform/shared/utils
mkdir -p /Users/a0247716/Pradips_Project/cbse-tutor-platform/shared/config
```

Create `shared/package.json`:
```json
{
  "name": "@likhapoha/shared",
  "version": "1.0.0",
  "main": "index.js",
  "license": "UNLICENSED",
  "private": true
}
```

### Step 1.2 — Set up npm workspaces in root `package.json`

```json
{
  "name": "cbse-tutor-platform",
  "private": true,
  "workspaces": ["frontend", "mobile", "shared"]
}
```

### Step 1.3 — Copy (do NOT move yet) shared JS into `shared/`

Copy these files from `frontend/src/` into `shared/`:
- `api/auth.js`, `api/lesson.js`, `api/doubt.js`, `api/mockTest.js`, `api/analytics.js`, `api/progress.js`, `api/syllabus.js`, `api/tts.js`
- `utils/markdownCleanup.js`, `utils/resolveSubscription.js`, `utils/subjectAccess.js`, `utils/syllabusDefaults.js`
- `config/subscriptionPlans.js`

**Keep the originals in `frontend/src/` untouched until the mobile app is working.**

### Step 1.4 — Verify web CI still passes

```bash
cd frontend && npx vitest run && npx eslint src/ --max-warnings 50
```

---

## Phase 2: Expo Project Bootstrap

### Step 2.1 — Prerequisites

```bash
npm install -g @expo/eas-cli
npx create-expo-app mobile --template tabs
cd mobile
```

### Step 2.2 — Install core dependencies

```bash
# Navigation
npx expo install expo-router react-native-screens react-native-safe-area-context

# Auth
npx expo install @supabase/supabase-js expo-auth-session expo-crypto expo-secure-store expo-web-browser

# LaTeX rendering (MVP approach)
npx expo install react-native-math-view

# Payments
npm install react-native-razorpay

# Markdown
npm install react-native-markdown-display

# Audio
npx expo install expo-av

# Push notifications
npx expo install expo-notifications

# Image compression
npx expo install expo-image-manipulator

# Shared package
npm install @likhapoha/shared@* --workspace=mobile
```

### Step 2.3 — Configure `app.json`

```json
{
  "expo": {
    "name": "Likha Poha AI",
    "slug": "likhapoha-ai",
    "version": "1.0.0",
    "orientation": "portrait",
    "icon": "./assets/icon.png",
    "splash": {
      "image": "./assets/splash.png",
      "resizeMode": "contain",
      "backgroundColor": "#6366f1"
    },
    "android": {
      "package": "in.likhapoha.app",
      "versionCode": 1,
      "adaptiveIcon": {
        "foregroundImage": "./assets/adaptive-icon.png",
        "backgroundColor": "#6366f1"
      },
      "permissions": ["INTERNET", "VIBRATE"]
    },
    "plugins": [
      ["expo-notifications", { "color": "#6366f1" }],
      "expo-secure-store",
      "expo-router"
    ]
  }
}
```

### Step 2.4 — Environment variables

Create `mobile/.env`:
```
EXPO_PUBLIC_API_BASE_URL=https://your-backend-domain.com
EXPO_PUBLIC_SUPABASE_URL=https://dpivlbbyzlbpwnwgajso.supabase.co
EXPO_PUBLIC_SUPABASE_ANON_KEY=<anon key — safe to expose>
EXPO_PUBLIC_RAZORPAY_KEY_ID=<your razorpay key id>
```

**Never put the service-role key or Razorpay secret in mobile env.**

---

## Phase 3: Authentication (Critical — Match Backend State Machine)

The backend OAuth state machine is authoritative. Mobile must follow the same rules as web.

### Supabase Client (mobile)

```ts
// mobile/lib/supabase.ts
import { createClient } from "@supabase/supabase-js";
import * as SecureStore from "expo-secure-store";

const ExpoSecureStoreAdapter = {
  getItem: (key: string) => SecureStore.getItemAsync(key),
  setItem: (key: string, value: string) => SecureStore.setItemAsync(key, value),
  removeItem: (key: string) => SecureStore.deleteItemAsync(key),
};

export const supabase = createClient(
  process.env.EXPO_PUBLIC_SUPABASE_URL!,
  process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY!,
  { auth: { storage: ExpoSecureStoreAdapter, autoRefreshToken: true, persistSession: true, detectSessionInUrl: false } }
);
```

**Key difference from web:** `detectSessionInUrl: false` (Expo handles deep links differently).  
**Token storage:** `expo-secure-store` instead of `localStorage`.

### Google OAuth (mobile)

```ts
// mobile/lib/googleAuth.ts
import * as WebBrowser from "expo-web-browser";
import * as AuthSession from "expo-auth-session";
import { supabase } from "./supabase";

WebBrowser.maybeCompleteAuthSession();

export async function signInWithGoogle() {
  const { data, error } = await supabase.auth.signInWithOAuth({
    provider: "google",
    options: {
      redirectTo: AuthSession.makeRedirectUri({ scheme: "likhapoha" }),
    },
  });
  if (data?.url) await WebBrowser.openAuthSessionAsync(data.url);
  return { error };
}
```

After OAuth completes, call `GET /api/auth/me` exactly as the web does — the same backend state machine applies.

---

## Phase 4: LaTeX Rendering Strategy

### MVP (Phase 1 mobile release)

Use `react-native-math-view` per math block. Performance is acceptable for ≤10 formulas per screen.

```tsx
// mobile/components/MathText.tsx
import MathView from "react-native-math-view";
import { normalizePlainExponents, normalizePlainAlgebra } from "@likhapoha/shared/utils/markdownCleanup";

export function MathText({ children }: { children: string }) {
  const normalized = normalizePlainAlgebra(normalizePlainExponents(children));
  if (!normalized.includes("$") && !normalized.includes("\\")) {
    return <Text>{normalized}</Text>;
  }
  const expr = normalized.replace(/^\$(.+)\$$/, "$1"); // strip outer $
  return <MathView math={expr} />;
}
```

### Production (Phase 2+)

Backend pre-renders math to SVG and stores in `lesson_cache_svg` column. Mobile fetches SVG string → renders as `<SvgXml>` via `react-native-svg`. Zero client-side math library needed.

**Migration required:**
```sql
-- backend/migrations/20260712_lesson_cache_svg.sql
ALTER TABLE lesson_cache ADD COLUMN IF NOT EXISTS svg_content TEXT;
```

**Backend update:** After `store_lesson_cache()`, call a background SVG renderer using MathJax Node.

---

## Phase 5: Screens to Build (Minimum for Play Store MVP)

| Screen | Priority | Complexity | Notes |
|---|---|---|---|
| Login / Signup | P0 | Low | Email + Google OAuth |
| Student Dashboard | P0 | Low | Same API as web |
| Lessons (select + generate) | P0 | **High** | LaTeX rendering + audio |
| Mock Test | P0 | Medium | Same API |
| Ask Doubt | P1 | Medium | — |
| Subscription Plans + Payment | P0 | Medium | Razorpay RN SDK |
| Formula Sheets | P1 | Medium | LaTeX |
| Exam Prep | P1 | Medium | JEE/NEET/CUET |
| Parent Dashboard | P2 | Medium | — |
| Profile / Settings | P0 | Low | — |

### Screen count for MVP: 6 screens (Login, Dashboard, Lessons, MockTest, Plans, Profile)

---

## Phase 6: Payments (Razorpay)

```bash
npm install react-native-razorpay
npx expo prebuild  # generates native code (required for native modules)
```

```ts
// mobile/lib/payment.ts
import RazorpayCheckout from "react-native-razorpay";
import { createPaymentOrder, verifyPayment } from "@likhapoha/shared/api/payments";

export async function initiatePayment(plan: string, user: any) {
  // Step 1: Create order via existing backend endpoint (unchanged)
  const order = await createPaymentOrder({ plan, user_id: user.id });

  // Step 2: Open Razorpay checkout
  const options = {
    description: `Likha Poha AI — ${plan}`,
    image: "https://your-cdn/logo.png",
    currency: "INR",
    key: process.env.EXPO_PUBLIC_RAZORPAY_KEY_ID,
    amount: order.amount,
    order_id: order.id,
    name: "Likha Poha AI",
    prefill: { email: user.email, contact: user.phone || "" },
    theme: { color: "#6366f1" },
  };

  return new Promise((resolve, reject) => {
    RazorpayCheckout.open(options)
      .then(async (data: any) => {
        // Step 3: Verify via existing backend endpoint (unchanged)
        await verifyPayment({
          razorpay_order_id: data.razorpay_order_id,
          razorpay_payment_id: data.razorpay_payment_id,
          razorpay_signature: data.razorpay_signature,
          plan,
        });
        resolve(data);
      })
      .catch(reject);
  });
}
```

**The backend `/api/payments/create-order` and `/api/payments/verify` endpoints are unchanged.**

---

## Phase 7: Push Notifications

### Backend addition (minor)

Add `push_token` column:
```sql
-- backend/migrations/20260712_push_tokens.sql
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS push_token TEXT;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS push_platform TEXT DEFAULT 'expo';
```

Add endpoint:
```python
# backend/app/routes/auth.py — add one new route
@router.post("/api/auth/register-push-token")
def register_push_token(body: PushTokenIn, user=Depends(require_student_or_parent_or_teacher)):
    db.table("profiles").update({"push_token": body.token}).eq("id", user.id).execute()
    return {"ok": True}
```

### Mobile registration

```ts
// mobile/hooks/usePushNotifications.ts
import * as Notifications from "expo-notifications";

export async function registerForPushNotifications(userId: string) {
  const { status } = await Notifications.requestPermissionsAsync();
  if (status !== "granted") return;
  const token = (await Notifications.getExpoPushTokenAsync()).data;
  await fetch(`${API_BASE}/api/auth/register-push-token`, {
    method: "POST",
    headers: { Authorization: `Bearer ${accessToken}`, "Content-Type": "application/json" },
    body: JSON.stringify({ token }),
  });
}
```

---

## Phase 8: EAS Build Setup (Android)

### Step 8.1 — Log in to EAS

```bash
eas login           # create account at expo.dev if needed
eas build:configure # creates eas.json
```

### Step 8.2 — Configure `eas.json`

```json
{
  "cli": { "version": ">= 5.0.0" },
  "build": {
    "development": {
      "developmentClient": true,
      "distribution": "internal",
      "android": { "buildType": "apk" }
    },
    "preview": {
      "distribution": "internal",
      "android": { "buildType": "apk" }
    },
    "production": {
      "android": { "buildType": "app-bundle" }
    }
  },
  "submit": {
    "production": {
      "android": {
        "serviceAccountKeyPath": "./google-play-service-account.json",
        "track": "internal"
      }
    }
  }
}
```

### Step 8.3 — Set EAS secrets (never in code)

```bash
eas secret:create --scope project --name SUPABASE_ANON_KEY --value "your-anon-key"
eas secret:create --scope project --name RAZORPAY_KEY_ID --value "your-key"
eas secret:create --scope project --name API_BASE_URL --value "https://your-backend.com"
```

### Step 8.4 — Build development APK (test on device)

```bash
cd mobile
eas build --platform android --profile development
```

### Step 8.5 — Build production AAB (for Play Store)

```bash
eas build --platform android --profile production
```

This produces a signed `.aab` (Android App Bundle) ready for Play Store upload.

---

## Phase 9: Google Play Store Submission — Step by Step

### Prerequisites before submitting

- [ ] Google Play Developer account ($25 one-time fee) at play.google.com/console
- [ ] App icon: 512×512 PNG (no alpha)
- [ ] Feature graphic: 1024×500 PNG
- [ ] Screenshots: at least 2 phone screenshots (1080×1920 or similar)
- [ ] Privacy policy URL (required — host a simple HTML page)
- [ ] Short description (≤80 chars)
- [ ] Full description (≤4000 chars)
- [ ] App content rating questionnaire completed
- [ ] Target audience set (since platform serves minors: set "Education", declare under-13 content)

### Step 9.1 — Create the app in Play Console

1. Go to [play.google.com/console](https://play.google.com/console)
2. Click **Create app**
3. App name: **Likha Poha AI**
4. Default language: **English (India)**
5. App or game: **App**
6. Free or paid: **Free** (Razorpay handles in-app purchases)
7. Accept policies → **Create app**

### Step 9.2 — Set up the store listing

Go to **Store presence → Main store listing**:
- App name: Likha Poha AI
- Short description: AI-powered CBSE tutoring for students Grade 5–12
- Full description: (include CBSE, AI lessons, mock tests, doubt solving, parent dashboard)
- Upload screenshots (at least phone screenshots)
- Upload feature graphic
- Upload icon

### Step 9.3 — Content rating

Go to **Policy → App content → Content rating**:
- Complete the questionnaire
- Category: **Education**
- Declare that app is directed at students under 13 (required since Grade 5 = ~10 years old)

### Step 9.4 — Target audience and content

Go to **Policy → App content → Target audience and content**:
- Target age group: **13 and up** OR **All ages** (depending on COPPA compliance)
- If targeting under-13: privacy policy must explicitly state no data collection from children

### Step 9.5 — Set up internal testing track

1. Go to **Testing → Internal testing**
2. Create a new release
3. Upload the `.aab` from EAS Build (or use `eas submit --platform android`)
4. Add testers (your email + team)
5. Publish to internal testing

```bash
# Or submit automatically via EAS:
eas submit --platform android --profile production
```

### Step 9.6 — Test thoroughly on internal track

Install on Android devices via the Play Store testing link. Test:
- [ ] Login (email + Google OAuth)
- [ ] Lesson generation + LaTeX rendering
- [ ] Mock test
- [ ] Payment flow (use Razorpay test mode key first)
- [ ] Audio playback
- [ ] Push notifications

### Step 9.7 — Promote to production

1. Go to **Testing → Internal testing → Release details**
2. Click **Promote release → Production**
3. Set rollout percentage: start with **10%** 
4. Submit for review (Google review takes 1–3 days for first submission)

### Step 9.8 — Ongoing releases

For every new release:
```bash
# Bump versionCode in app.json (MUST increment every time)
# Bump version string for user-facing display

eas build --platform android --profile production
eas submit --platform android --profile production
```

---

## Phase 10: OTA Updates (Ship Fixes Without App Store Review)

EAS Update lets you push JS/asset changes instantly without a full AAB build.

```bash
npx expo install expo-updates
```

```bash
# Push a JS fix to all users immediately (no review needed)
eas update --branch production --message "Fix LaTeX rendering in Lessons"
```

**What OTA can update:** JS code, assets (images, fonts), `markdownCleanup.js` fixes, API changes  
**What requires a full build:** New native modules, Android permissions, Expo SDK upgrades

> This is critical for this platform. Bug fixes like normalization pipeline improvements
> can be shipped to all Android users within minutes via OTA, matching the web's instant deploy.

---

## Phase 11: CI Pipeline for Mobile

Add to GitHub Actions (`.github/workflows/mobile.yml`):

```yaml
name: Mobile CI
on:
  push:
    paths:
      - 'mobile/**'
      - 'shared/**'
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - run: npm install
      - run: cd mobile && npx tsc --noEmit     # TypeScript check
      - run: cd mobile && npx jest              # unit tests
```

**Path filter ensures:** A change to `frontend/` does NOT trigger the mobile CI, and vice versa.

---

## Phase 12: Backend Additions Required

Only 2 additions to the backend are needed for the mobile app. Both are additive and do not affect the web:

| Addition | File | Purpose | Breaking? |
|---|---|---|---|
| `push_token` + `push_platform` columns | migration `20260712_push_tokens.sql` | Store Expo push token | No — optional column |
| `POST /api/auth/register-push-token` | `backend/app/routes/auth.py` | Store/update push token | No — new endpoint |
| `lesson_cache_svg` column | migration `20260712_lesson_cache_svg.sql` | Phase 2 math pre-render | No — optional column |

The mobile app calls all existing endpoints (`/api/lesson`, `/api/mock-test`, `/api/student/dashboard/summary`, etc.) with the same JWT auth. Zero other backend changes.

---

## Phase 13: Migrating `frontend/src/` → `shared/` (Without Breaking Web)

This migration is optional for MVP but required before v1.0 to prevent code drift.

### Migration order (safest)

Do one file at a time. Each step: copy → wire → test → commit.

```bash
# Example: migrate markdownCleanup.js

# Step A: copy to shared (already done in Phase 1)
# cp frontend/src/utils/markdownCleanup.js shared/utils/markdownCleanup.js

# Step B: make frontend re-export from shared
echo 'export * from "@likhapoha/shared/utils/markdownCleanup";' \
  > frontend/src/utils/markdownCleanup.js

# Step C: run web CI — must still pass
cd frontend && npx vitest run && npx eslint src/ --max-warnings 50

# Step D: run mobile CI
cd mobile && npx tsc --noEmit

# Step E: commit
git add shared/utils/markdownCleanup.js frontend/src/utils/markdownCleanup.js
git commit -m "refactor: move markdownCleanup to shared/ package"
```

Repeat for each file. This migration can be done alongside feature development.

---

## Phase 14: iOS (Future — After Android is Live)

When ready for Apple App Store:

1. **Apple Developer account** ($99/year)
2. **EAS Build for iOS:**
   ```bash
   eas build --platform ios --profile production
   ```
3. **Key difference:** Apple requires in-app purchases for digital subscriptions sold in the app (30% cut). Options:
   - Remove Razorpay from iOS app and route users to web for payment
   - Implement StoreKit via `expo-in-app-purchases` (loses Razorpay integration)
   - Most indie edtech apps use option 1 — "subscription available on web" notice in the iOS app

---

## Summary: What You Need To Do (In Order)

### Week 1 — Foundation
- [ ] `npm install -g @expo/eas-cli`
- [ ] Create Google Play Developer account ($25)
- [ ] Create Expo account at expo.dev (free)
- [ ] Set up `shared/` package + workspace root `package.json`
- [ ] Run `npx create-expo-app mobile --template tabs` inside the repo

### Week 2 — Auth + Core Screens
- [ ] Implement Supabase client with `expo-secure-store`
- [ ] Implement Google OAuth with `expo-auth-session`
- [ ] Wire `GET /api/auth/me` and the OAuth state machine
- [ ] Build Login, Signup screens
- [ ] Build Student Dashboard screen (uses `GET /api/student/dashboard/summary`)

### Week 3 — Lessons + LaTeX
- [ ] Build Lessons screen with syllabus selectors
- [ ] Implement `MathText` component (`react-native-math-view`)
- [ ] Wire lesson generation API
- [ ] Add `react-native-markdown-display` for lesson content
- [ ] Audio playback with `expo-av` (uses cached URLs from existing backend)

### Week 4 — Mock Test + Payment
- [ ] Build Mock Test screen
- [ ] Build Subscription Plans screen
- [ ] Implement Razorpay with `react-native-razorpay`
- [ ] `npx expo prebuild` to generate native Android project
- [ ] Build development APK: `eas build --platform android --profile development`
- [ ] Install and test on physical Android device

### Week 5 — Polish + Play Store
- [ ] Prepare store assets (icon, screenshots, feature graphic)
- [ ] Write store listing (short + full description)
- [ ] Complete content rating questionnaire
- [ ] Build production AAB: `eas build --platform android --profile production`
- [ ] Submit to internal testing track: `eas submit --platform android`
- [ ] Test on internal track
- [ ] Promote to production (10% rollout)

### Week 6+ — Push notifications + OTA fixes
- [ ] Register `push_token` endpoint in backend
- [ ] Implement push notification registration in mobile
- [ ] Ship first OTA update: `eas update --branch production`

---

## Non-Negotiable Rules for Mobile Development

1. **`frontend/` is never modified** during mobile work. All shared code lives in `shared/`.
2. **Web CI must pass before every mobile commit.** Run `cd frontend && npx vitest run && npx eslint src/ --max-warnings 50` before pushing.
3. **Shared fixes go in `shared/`**, never duplicated in `mobile/`.
4. **Never put secrets in mobile code.** Use `EXPO_PUBLIC_*` for public keys only; secrets stay in EAS secrets and backend env.
5. **Never put the Supabase service-role key in the mobile app.** The anon key is the only Supabase key in the app.
6. **Backend auth rules apply equally to mobile.** The backend does not have a separate auth path for mobile. Same JWT, same role checks, same feature authorization.
7. **`versionCode` in `app.json` must increment with every Play Store upload.** Never reuse a version code.
8. **Test payments with Razorpay test mode keys** before switching to live keys.
9. **OTA updates only for JS/asset changes.** Never try to OTA a native module or permission change — it will silently fail.
10. **iOS payments via web.** When iOS version is built, do not implement Razorpay in the iOS build — route users to the web app for subscription purchase to avoid Apple's 30% cut.

---

## Assets Required Before Play Store Submission

| Asset | Size | Format | Notes |
|---|---|---|---|
| App icon | 512×512 px | PNG, no transparency | Used in Play Store listing |
| Adaptive icon foreground | 432×432 px | PNG, transparent bg | Android home screen icon |
| Splash screen | 1284×2778 px | PNG | Shown on app launch |
| Feature graphic | 1024×500 px | PNG or JPEG | Play Store banner |
| Phone screenshots | 1080×1920 px min | PNG or JPEG | Min 2, max 8 |
| Privacy policy | Any URL | HTML page | Required for apps with accounts |

---

## Privacy Policy Requirements (Mandatory)

Google Play requires a privacy policy for any app that handles personal data. This app handles:
- Email addresses
- Names
- Grades/educational data (children's academic progress)
- Payment information (handled by Razorpay, not stored by us)

Host a privacy policy page at a URL like `https://likhapoha.in/privacy`. It must cover:
- What data is collected (email, name, grade, progress)
- How data is stored (Supabase, India/US servers)
- That payment data is processed by Razorpay, not stored by the app
- COPPA/DPDP compliance note for students under 13
- Contact email for data requests

---

_See also: `docs/README.md` for the full document index._
