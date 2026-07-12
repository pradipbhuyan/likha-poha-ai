/**
 * Root layout with ErrorBoundary — shows crash errors ON SCREEN
 * so we can diagnose without ADB.
 */
import { useEffect, useState, Component } from "react";
import { Slot, useRouter, useSegments } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { View, Text, ScrollView, StyleSheet } from "react-native";
import { supabase } from "../lib/supabase";

// ── On-screen error display ──────────────────────────────────────────────────
class ErrorBoundary extends Component<{ children: any }, { error: any }> {
  constructor(props: any) {
    super(props);
    this.state = { error: null };
  }
  static getDerivedStateFromError(error: any) {
    return { error };
  }
  render() {
    if (this.state.error) {
      return (
        <View style={eb.container}>
          <Text style={eb.title}>🔴 App Crash (debug info)</Text>
          <ScrollView>
            <Text style={eb.msg}>{String(this.state.error?.message ?? this.state.error)}</Text>
            <Text style={eb.stack}>{String(this.state.error?.stack ?? "")}</Text>
          </ScrollView>
        </View>
      );
    }
    return this.props.children;
  }
}
const eb = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#1a1a1a", padding: 20, paddingTop: 60 },
  title: { color: "#ff4444", fontSize: 18, fontWeight: "bold", marginBottom: 16 },
  msg: { color: "#ff9999", fontSize: 14, lineHeight: 22, marginBottom: 12 },
  stack: { color: "#888", fontSize: 11, lineHeight: 18 },
});

// ── Root navigation guard ────────────────────────────────────────────────────
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
    <ErrorBoundary>
      <StatusBar style="auto" />
      <RootNavigation />
    </ErrorBoundary>
  );
}
