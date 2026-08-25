/**
 * Shared user profile + feature-entitlement context.
 *
 * Fetches GET /api/auth/me and GET /api/subscription/features exactly once
 * per session — mounted once at the tabs layout — instead of the 7
 * independent per-screen fetches this replaces: the tabs layout itself,
 * doubt.tsx, exemplar.tsx, formula.tsx, lessons.tsx, learn.tsx, and
 * mocktest.tsx each used to call both endpoints on their own.
 *
 * This mattered beyond just avoiding redundant network calls: exemplar.tsx's
 * own read of the /api/subscription/features response was finding #1 in
 * docs/ACCESS_CONTROL_ARCHITECTURE_BLUEPRINT.md — a screen quietly trusting
 * a locally re-fetched, ad hoc slice of a response nobody else validated.
 * One typed shape, fetched in one place, is harder to misread than seven
 * separately-shaped `any`s.
 *
 * Each screen still owns its own local derived state (its own `grade`
 * selector seeded from `profile.grade`, its own `subject` default, etc.) —
 * this context only centralizes the network fetch and the response shape,
 * not per-screen UI logic. Every consumer's existing fallback/default
 * values are preserved exactly; see the field-by-field survey this was
 * built from for the original per-screen behavior.
 */
import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from "react";
import { authFetch } from "./authFetch";

export interface UserProfile {
  grade: string | null;
  stream: string;
  cbseSubjects: string[];
  username: string;
  email: string;
  canReportIssues: boolean;
}

export interface FeatureAccess {
  allowed: boolean;
  limited: boolean;
}

interface UserProfileContextValue {
  profile: UserProfile | null;
  features: Record<string, FeatureAccess>;
  hasFullAccess: boolean;
  loading: boolean;
  /** Re-fetch both endpoints — none of the 7 original call sites did this
   *  themselves (all were fetch-once-on-mount), exposed here for screens
   *  added later that might need it (e.g. after a subscription purchase). */
  refresh: () => void;
}

const UserProfileContext = createContext<UserProfileContextValue>({
  profile: null,
  features: {},
  hasFullAccess: false,
  loading: true,
  refresh: () => {},
});

export function UserProfileProvider({ children }: { children: ReactNode }) {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [features, setFeatures] = useState<Record<string, FeatureAccess>>({});
  const [hasFullAccess, setHasFullAccess] = useState(false);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([
      authFetch("/api/auth/me").catch(() => null),
      authFetch("/api/subscription/features").catch(() => null),
    ]).then(([me, featureData]: [any, any]) => {
      // Resolve `profile` unconditionally once the fetch settles, whether
      // or not `me` came back — several consumers (formula.tsx, lessons.tsx,
      // learn.tsx) treat "profile resolved but grade unknown" as "default to
      // Grade 9" as a fail-safe, matching what `me?.grade` would have
      // produced from a null `me` in their original per-screen fetches.
      // Leaving `profile` at `null` forever on a failed fetch would silently
      // change that fail-safe into "never lock anything," the same class of
      // bug as the OAuth/me check that motivated this file.
      setProfile({
        grade: me?.grade ?? null,
        stream: me?.stream ?? "",
        cbseSubjects: me?.cbse_subjects ?? [],
        username: me?.username ?? me?.email?.split("@")[0] ?? "student",
        email: me?.email ?? "",
        canReportIssues: !!me?.can_report_issues,
      });
      if (featureData?.features) setFeatures(featureData.features);
      if (featureData?.has_full_access !== undefined) {
        setHasFullAccess(featureData.has_full_access ?? false);
      }
    }).finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  return (
    <UserProfileContext.Provider value={{ profile, features, hasFullAccess, loading, refresh: load }}>
      {children}
    </UserProfileContext.Provider>
  );
}

export function useUserProfile() {
  return useContext(UserProfileContext);
}
