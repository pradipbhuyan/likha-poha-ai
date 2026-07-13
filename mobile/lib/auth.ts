/**
 * Authentication helpers for Likha Poha AI mobile app.
 *
 * Mirrors the web OAuth state machine (App.jsx / auth.py):
 *   1. Sign in → Supabase returns session
 *   2. Call GET /api/auth/me to check oauth_profile_complete + needs_role_selection
 *   3. If needs_role_selection → show role picker → POST /api/auth/oauth/complete-profile
 *   4. If profile_complete → navigate to dashboard
 */
import * as WebBrowser from "expo-web-browser";
import * as AuthSession from "expo-auth-session";
import { supabase } from "./supabase";
import { API_BASE_URL } from "../constants";

WebBrowser.maybeCompleteAuthSession();

/**
 * Sign in with Google OAuth using Supabase + expo-web-browser.
 *
 * Returns the OAuth URL to open — caller opens the browser and exchanges
 * the callback URL for a Supabase session via exchangeCodeForSession().
 *
 * Using skipBrowserRedirect: true so WE control when the browser opens
 * (prevents Supabase from triggering a web-only automatic redirect).
 */
export async function signInWithGoogle(): Promise<{ url: string | null; redirectUri: string; error: Error | null }> {
  const redirectUri = AuthSession.makeRedirectUri({ scheme: "likhapoha" });
  const { data, error } = await supabase.auth.signInWithOAuth({
    provider: "google",
    options: {
      redirectTo: redirectUri,
      skipBrowserRedirect: true,
    },
  });
  if (error) return { url: null, redirectUri, error };
  return { url: data.url ?? null, redirectUri, error: null };
}

/** Sign in with email + password. */
export async function signInWithEmail(email: string, password: string) {
  return supabase.auth.signInWithPassword({ email, password });
}

/** Sign up with email + password + role. */
export async function signUpWithEmail(
  email: string,
  password: string,
  role: "student" | "parent",
  grade?: string,
  stream?: string   // Grade 11/12 students: PCM|PCB|PCMB|Commerce|Humanities
) {
  return supabase.auth.signUp({
    email,
    password,
    options: {
      data: { role, grade: grade ?? null, stream: stream ?? null },
    },
  });
}

/** Sign out. */
export async function signOut() {
  return supabase.auth.signOut();
}

/**
 * Check the backend OAuth state machine after sign-in.
 * Returns the same shape as GET /api/auth/me on the web.
 */
export async function checkAuthState(accessToken: string) {
  const res = await fetch(`${API_BASE_URL}/api/auth/me`, {
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
  });
  if (!res.ok) throw new Error(`/api/auth/me returned ${res.status}`);
  return res.json(); // { profile_complete, needs_role_selection, role, ... }
}

/** Complete OAuth profile (assign role). Mirrors POST /api/auth/oauth/complete-profile. */
export async function completeOAuthProfile(
  accessToken: string,
  role: string,
  grade?: string,
  stream?: string   // Grade 11/12 students: PCM|PCB|PCMB|Commerce|Humanities
) {
  const res = await fetch(`${API_BASE_URL}/api/auth/oauth/complete-profile`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ role, grade: grade ?? null, stream: stream ?? null }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `complete-profile returned ${res.status}`);
  }
  return res.json();
}
