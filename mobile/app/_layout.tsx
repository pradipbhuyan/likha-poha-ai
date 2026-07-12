/**
 * Root layout — Expo Router entry point.
 * Uses <Slot /> (simplest Expo Router pattern) with a session-based
 * redirect guard. No Stack config at root level prevents navigation conflicts.
 */
import { useEffect, useState } from "react";
import { Slot, useRouter, useSegments } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { supabase } from "../lib/supabase";

export default function RootLayout() {
  const [session, setSession] = useState<any>(null);
  const [initialized, setInitialized] = useState(false);
  const router = useRouter();
  const segments = useSegments();

  useEffect(() => {
    // Get initial session
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session ?? null);
      setInitialized(true);
    });

    // Listen for auth state changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (_event, session) => setSession(session ?? null)
    );
    return () => subscription.unsubscribe();
  }, []);

  useEffect(() => {
    if (!initialized) return;
    const inAuth = segments[0] === "auth";
    if (session && inAuth) {
      router.replace("/(tabs)");
    } else if (!session && !inAuth) {
      router.replace("/auth/login");
    }
  }, [session, initialized, segments]);

  return (
    <>
      <StatusBar style="auto" />
      <Slot />
    </>
  );
}
