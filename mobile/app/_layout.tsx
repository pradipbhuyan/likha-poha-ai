/**
 * Root layout — manages authentication state machine.
 *
 * After every session change:
 *   1. Call GET /api/auth/me to check oauth_profile_complete + needs_role_selection
 *   2. "needs_role"  → /auth/role-select  (Google OAuth new user)
 *   3. "ready"       → /(tabs)            (fully authenticated)
 *   4. "unauthed"    → /auth/login
 *
 * This mirrors the web App.jsx OAuth state machine so mobile Google auth
 * follows the same backend-authoritative profile_complete check.
 */
import { useEffect, useRef, useState, useCallback } from "react";
import { Stack, useRouter, useSegments } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { supabase } from "../lib/supabase";
import { checkAuthState } from "../lib/auth";

type AuthState = "loading" | "unauthenticated" | "needs_role" | "ready";

function RootNavigation() {
  const [authState, setAuthState] = useState<AuthState>("loading");
  const router = useRouter();
  const segments = useSegments();

  // Track whether the user has ever been authenticated in this session.
  // Prevents a transient SIGNED_OUT (e.g. during OAuth token exchange) from
  // routing an already-authenticated user back to the login screen.
  const wasAuthenticated = useRef(false);

  /**
   * Process a Supabase session by calling GET /api/auth/me.
   * Sets authState based on backend profile_complete flag.
   * Falls back to "ready" if backend is unreachable (graceful degradation).
   */
  const processSession = useCallback(async (sess: any) => {
    if (!sess) {
      setAuthState("unauthenticated");
      return;
    }
    try {
      const meData = await checkAuthState(sess.access_token);
      setAuthState(meData.needs_role_selection ? "needs_role" : "ready");
    } catch {
      // Backend unreachable (e.g. offline, dev) — treat as authenticated
      setAuthState("ready");
    }
  }, []);

  // Bootstrap: check existing session on mount, then listen for changes
  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      processSession(data.session ?? null);
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (_event, sess) => processSession(sess ?? null)
    );

    return () => subscription.unsubscribe();
  }, []); // eslint-disable-line

  // Route based on auth state
  useEffect(() => {
    if (authState === "loading") return;

    const segs = segments as string[];
    const inAuth = segs[0] === "auth";
    const onRoleSelect = segs[0] === "auth" && segs[1] === "role-select";

    // Mark as authenticated once we've confirmed a valid session.
    // After this point, a transient SIGNED_OUT (OAuth exchange) won't kick
    // the user back to login — only an explicit sign-out should do that.
    if (authState === "ready" || authState === "needs_role") {
      wasAuthenticated.current = true;
    }

    if (authState === "ready" && inAuth) {
      router.replace("/(tabs)");
    } else if (authState === "needs_role" && !onRoleSelect) {
      router.replace("/auth/role-select" as any);
    } else if (authState === "unauthenticated" && !inAuth && !wasAuthenticated.current) {
      // Only route to login if user was never authenticated in this session.
      // wasAuthenticated.current = true means they logged in successfully but
      // a transient SIGNED_OUT fired (OAuth exchange) — don't send them to login.
      router.replace("/auth/login");
    }
  }, [authState, segments]); // eslint-disable-line

  return (
    <Stack screenOptions={{ headerShown: false }} />
  );
}

export default function RootLayout() {
  return (
    <SafeAreaProvider>
      <StatusBar style="auto" />
      <RootNavigation />
    </SafeAreaProvider>
  );
}
