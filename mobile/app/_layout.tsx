import { useEffect, useState } from "react";
import { Slot, useRouter, useSegments } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { supabase } from "../lib/supabase";

function RootNavigation() {
  const [session, setSession] = useState<any>(null);
  const [initialized, setInitialized] = useState(false);
  const router = useRouter();
  const segments = useSegments();

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session ?? null);
      setInitialized(true);
    });
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (_event, session) => setSession(session ?? null)
    );
    return () => subscription.unsubscribe();
  }, []);

  useEffect(() => {
    if (!initialized) return;
    const inAuth = segments[0] === "auth";
    if (session && inAuth) router.replace("/(tabs)");
    else if (!session && !inAuth) router.replace("/auth/login");
  }, [session, initialized, segments]);

  return <Slot />;
}

export default function RootLayout() {
  return (
    <>
      <StatusBar style="auto" />
      <RootNavigation />
    </>
  );
}
