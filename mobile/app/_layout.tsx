/**
 * Root layout — Expo Router entry point.
 *
 * Handles:
 * - Session check on app launch
 * - Route guard: redirect to /auth/login if not signed in
 * - Route guard: redirect to (tabs) if already signed in
 */
import { useEffect, useState } from "react";
import { Stack, useRouter, useSegments, useNavigationContainerRef } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { supabase } from "../lib/supabase";

export default function RootLayout() {
  const [session, setSession] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();
  const segments = useSegments();
  const navigationRef = useNavigationContainerRef();
  const [navigationReady, setNavigationReady] = useState(false);

  // Wait for navigation container to be ready before any redirects
  useEffect(() => {
    const unsubscribe = navigationRef?.addListener?.("state", () => {});
    if (navigationRef?.isReady?.()) {
      setNavigationReady(true);
    } else {
      const timer = setTimeout(() => setNavigationReady(true), 200);
      return () => clearTimeout(timer);
    }
    return unsubscribe;
  }, [navigationRef]);

  useEffect(() => {
    // Check existing session on mount
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setLoading(false);
    });

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (_event, session) => {
        setSession(session);
      }
    );

    return () => subscription.unsubscribe();
  }, []);

  useEffect(() => {
    if (loading || !navigationReady) return;

    const inAuthGroup = segments[0] === "auth";

    if (!session && !inAuthGroup) {
      // No session → send to login
      router.replace("/auth/login");
    } else if (session && inAuthGroup) {
      // Has session → send to dashboard
      router.replace("/(tabs)");
    }
  }, [session, segments, loading, navigationReady]);

  return (
    <>
      <StatusBar style="auto" />
      <Stack screenOptions={{ headerShown: false }}>
        <Stack.Screen name="(tabs)" />
        <Stack.Screen name="auth" />
      </Stack>
    </>
  );
}
