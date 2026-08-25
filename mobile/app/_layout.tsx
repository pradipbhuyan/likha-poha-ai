/**
 * Root layout — manages authentication state machine.
 *
 * After every session change:
 *   1. Call GET /api/auth/me (with retry) to check oauth_profile_complete + needs_role_selection
 *   2. "needs_role"  → /auth/role-select  (Google OAuth new user)
 *   3. "ready"       → /(tabs)            (fully authenticated)
 *   4. "unauthed"    → /auth/login
 *   5. "error"       → blocking retry screen (see below)
 *
 * This mirrors the web App.jsx OAuth state machine so mobile Google auth
 * follows the same backend-authoritative profile_complete check.
 *
 * This is also the single place in the app that calls GET /api/auth/me to
 * decide auth routing — login.tsx's OAuth handler used to make its own
 * independent call and route on it too, racing this one. It no longer
 * does (see login.tsx); every session change, however it happened, is
 * routed from exactly here.
 */
import { useEffect, useRef, useState, useCallback } from "react";
import { View, Text, TouchableOpacity, ActivityIndicator, StyleSheet } from "react-native";
import { Stack, useRouter, useSegments } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { supabase } from "../lib/supabase";
import { checkAuthStateWithRetry } from "../lib/auth";
import { useTheme } from "../lib/theme";
import { BRAND_COLOR } from "../constants";

type AuthState = "loading" | "unauthenticated" | "needs_role" | "ready" | "error";

/**
 * Shown when checkAuthStateWithRetry exhausts its retries — e.g. offline, or
 * the backend is genuinely down. Deliberately blocking: the alternative
 * (silently treating this as "ready") is what let a brand-new Google
 * sign-in skip the role-select picker and land on the dashboard with the
 * database's placeholder Grade 9/student values whenever this one request
 * had a bad moment. Fail closed instead, with a way to retry.
 */
function AuthCheckErrorScreen({ onRetry }: { onRetry: () => void }) {
  const { colors } = useTheme();
  return (
    <View style={[styles.errorScreen, { backgroundColor: colors.bg }]}>
      <Text style={[styles.errorTitle, { color: colors.text }]}>Couldn&rsquo;t verify your account</Text>
      <Text style={[styles.errorBody, { color: colors.textMuted }]}>
        Check your connection and try again.
      </Text>
      <TouchableOpacity style={[styles.retryBtn, { backgroundColor: BRAND_COLOR }]} onPress={onRetry}>
        <Text style={styles.retryBtnText}>Try again</Text>
      </TouchableOpacity>
    </View>
  );
}

function RootNavigation() {
  const [authState, setAuthState] = useState<AuthState>("loading");
  const router = useRouter();
  const segments = useSegments();

  // Track whether the user has ever been authenticated in this session.
  // Prevents a transient SIGNED_OUT (e.g. during OAuth token exchange) from
  // routing an already-authenticated user back to the login screen.
  const wasAuthenticated = useRef(false);

  // Last session we were asked to process, so the retry button on the error
  // screen can re-run the same check rather than needing a fresh sign-in.
  const lastSessionRef = useRef<any>(null);

  /**
   * Process a Supabase session by calling GET /api/auth/me (with retry).
   * Sets authState based on backend profile_complete flag. On repeated
   * failure, fails closed to "error" rather than assuming "ready" —
   * see AuthCheckErrorScreen for why.
   */
  const processSession = useCallback(async (sess: any) => {
    lastSessionRef.current = sess;
    if (!sess) {
      setAuthState("unauthenticated");
      return;
    }
    try {
      const meData = await checkAuthStateWithRetry(sess.access_token);
      setAuthState(meData.needs_role_selection ? "needs_role" : "ready");
    } catch {
      setAuthState("error");
    }
  }, []);

  const retryLastSession = useCallback(() => {
    setAuthState("loading");
    processSession(lastSessionRef.current);
  }, [processSession]);

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
    if (authState === "loading" || authState === "error") return;

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

  if (authState === "error") {
    return <AuthCheckErrorScreen onRetry={retryLastSession} />;
  }

  if (authState === "loading") {
    return (
      <View style={styles.loadingScreen}>
        <ActivityIndicator size="large" color={BRAND_COLOR} />
      </View>
    );
  }

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

const styles = StyleSheet.create({
  loadingScreen: { flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: "#f8fafc" },
  errorScreen: { flex: 1, alignItems: "center", justifyContent: "center", padding: 32, gap: 8 },
  errorTitle: { fontSize: 17, fontWeight: "700", textAlign: "center" },
  errorBody: { fontSize: 14, textAlign: "center", marginBottom: 16 },
  retryBtn: { borderRadius: 12, paddingVertical: 13, paddingHorizontal: 28 },
  retryBtnText: { color: "#fff", fontSize: 15, fontWeight: "700" },
});
