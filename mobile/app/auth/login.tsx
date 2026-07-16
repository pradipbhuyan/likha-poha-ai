/**
 * Login screen — email/password + Google OAuth.
 * Supports light and dark mode via useTheme().
 */
import { useState, useRef } from "react";
import {
  View, Text, TextInput, TouchableOpacity, Image,
  StyleSheet, KeyboardAvoidingView, Platform, ActivityIndicator,
  ScrollView, Modal,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { StatusBar } from "expo-status-bar";
import { useRouter } from "expo-router";
import * as WebBrowser from "expo-web-browser";
import { Feather } from "@expo/vector-icons";
import { supabase } from "../../lib/supabase";
import { signInWithGoogle, checkAuthState } from "../../lib/auth";
import { useTheme } from "../../lib/theme";
import { BRAND_COLOR, API_BASE_URL } from "../../constants";

// react-native-webview requires a native build (not in Expo Go).
// Dynamic require so the app doesn't crash when running in Expo Go.
let NativeWebView: any = null;
try { NativeWebView = require("react-native-webview").WebView; } catch { /* Expo Go */ }

/**
 * WebView-based Google OAuth modal.
 *
 * Why WebView instead of WebBrowser.openAuthSessionAsync (Chrome Custom Tab):
 * - Android WebView respects the app's network_security_config.xml, which embeds
 *   the corporate Zscaler CA certs (@raw/zscaler_cert_0/1/2).
 * - Chrome Custom Tab uses Chrome's own cert store — Zscaler intercepts HTTPS
 *   and presents its cert, which Chrome does NOT trust → NET::ERR_CERT_AUTHORITY_INVALID.
 * - WebView does trust it (via network_security_config) → OAuth succeeds on corporate WiFi.
 */
function GoogleOAuthWebView({
  url,
  redirectUri,
  onSuccess,
  onCancel,
}: {
  url: string;
  redirectUri: string;
  onSuccess: (callbackUrl: string) => void;
  onCancel: () => void;
}) {
  const { colors } = useTheme();
  const [loading, setLoading] = useState(true);

  function handleNavChange(navState: { url?: string }) {
    const navUrl = navState.url ?? "";
    console.log("[WebView] navChange:", navUrl.substring(0, 80));
    // Detect when the OAuth callback redirects back to our app scheme
    // Also catch when Supabase redirects to likhapoha.in with a code param
    if (
      navUrl.startsWith("likhapoha://") ||
      navUrl.startsWith(redirectUri) ||
      (navUrl.startsWith("https://likhapoha.in") && navUrl.includes("code="))
    ) {
      console.log("[WebView] CAUGHT callback!");
      onSuccess(navUrl);
    }
  }

  return (
    <Modal animationType="slide" visible onRequestClose={onCancel}>
      <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }} edges={["top"]}>
        {/* Header */}
        <View style={{ flexDirection: "row", alignItems: "center", paddingHorizontal: 16, paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: colors.border, backgroundColor: colors.surface }}>
          <TouchableOpacity onPress={onCancel} style={{ padding: 6 }}>
            <Feather name="x" size={22} color={colors.text} />
          </TouchableOpacity>
          <Text style={{ flex: 1, textAlign: "center", fontWeight: "600", fontSize: 15, color: colors.text }}>Sign in with Google</Text>
          <View style={{ width: 34 }} />
        </View>
        {loading && (
          <View style={{ position: "absolute", top: 80, left: 0, right: 0, alignItems: "center", zIndex: 10 }}>
            <ActivityIndicator size="large" color={BRAND_COLOR} />
          </View>
        )}
        {NativeWebView && (
          <NativeWebView
            source={{ uri: url }}
            onNavigationStateChange={handleNavChange}
            onLoadStart={() => setLoading(true)}
            onLoadEnd={() => setLoading(false)}
            javaScriptEnabled
            domStorageEnabled
            style={{ flex: 1, backgroundColor: colors.bg }}
            // Override user agent to Chrome for Android — Google blocks OAuth in WebViews
            // because the default Android WebView UA contains "wv" (Error 403: disallowed_useragent).
            // Chrome UA does NOT contain "wv" so Google allows the OAuth flow.
            userAgent="Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36"
            onShouldStartLoadWithRequest={(req: { url: string }) => {
              console.log("[WebView] shouldLoad:", req.url.substring(0, 80));
              // Intercept the OAuth callback deep link (likhapoha://)
              // Also intercept https://likhapoha.in in case Supabase redirects there
              // when likhapoha:// isn't in its allowed redirect URL list yet
              if (
                req.url.startsWith("likhapoha://") ||
                req.url.startsWith(redirectUri) ||
                (req.url.startsWith("https://likhapoha.in") && req.url.includes("code="))
              ) {
                console.log("[WebView] INTERCEPTED callback!");
                onSuccess(req.url); return false;
              }
              return true;
            }}
          />
        )}
      </SafeAreaView>
    </Modal>
  );
}

export default function LoginScreen() {
  const router = useRouter();
  const { colors } = useTheme();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  async function handleLogin() {
    if (!email.trim() || !password) { setErrorMsg("Please enter your email or username and password."); return; }
    setLoading(true); setErrorMsg("");
    try {
      let loginEmail = email.trim().toLowerCase();

      // Username login — if input has no @, resolve to email
      if (!loginEmail.includes("@")) {
        // Try backend first; fall back to Supabase direct query (works when backend is unreachable)
        let resolved = false;
        try {
          const res = await fetch(`${API_BASE_URL}/api/auth/lookup-email/${encodeURIComponent(loginEmail)}`);
          if (res.ok) {
            const data = await res.json();
            loginEmail = data.email;
            resolved = true;
          }
        } catch { /* backend unreachable — try Supabase directly */ }

        if (!resolved) {
          // Direct Supabase query — works without backend, uses anon key
          const { data: rows } = await supabase
            .from("profiles")
            .select("email")
            .ilike("username", loginEmail)
            .limit(1);
          if (rows && rows.length > 0 && rows[0].email) {
            loginEmail = rows[0].email;
          } else {
            setErrorMsg("Username not found. Please check your username or use your email.");
            setLoading(false);
            return;
          }
        }
      }

      const { error } = await supabase.auth.signInWithPassword({ email: loginEmail, password });
      if (error) setErrorMsg(error.message);
    } catch (e: any) { setErrorMsg(e?.message ?? "Login failed. Please try again."); }
    finally { setLoading(false); }
  }

  const [oauthUrl, setOauthUrl] = useState<string | null>(null);
  const [oauthRedirectUri, setOauthRedirectUri] = useState<string>("");
  // Guard: prevents handleNavChange + onShouldStartLoadWithRequest both triggering exchange
  const oauthExchangeInProgress = useRef(false);

  async function handleGoogleLogin() {
    setGoogleLoading(true); setErrorMsg("");
    try {
      const { url, redirectUri, error } = await signInWithGoogle();
      if (error || !url) throw error ?? new Error("Could not start Google sign-in.");

      if (NativeWebView) {
        // Native APK build: use WebView modal — respects network_security_config.xml (Zscaler certs)
        console.log("[OAuth] redirectUri:", redirectUri);
        console.log("[OAuth] oauthUrl prefix:", (url || "").substring(0, 80));
        setOauthRedirectUri(redirectUri);
        setOauthUrl(url);
        setGoogleLoading(false);
      } else {
        // Expo Go fallback: use Chrome Custom Tab (requires mobile data on Zscaler networks)
        const result = await WebBrowser.openAuthSessionAsync(url, redirectUri);
        if (result.type === "success" && result.url) {
          const { error: ex } = await supabase.auth.exchangeCodeForSession(result.url);
          if (ex) throw ex;
        }
        setGoogleLoading(false);
      }
    } catch (e: any) {
      const msg: string = e?.message ?? "Google sign-in failed.";
      if (msg.includes("network") || msg.includes("fetch")) setErrorMsg("Network error. Please check your connection.");
      else if (msg.includes("OAuth") || msg.includes("provider")) setErrorMsg("Google sign-in is not configured.");
      else setErrorMsg(msg);
      setGoogleLoading(false);
    }
  }

  async function handleOAuthSuccess(callbackUrl: string) {
    // Prevent double-calling: both onNavigationStateChange and onShouldStartLoadWithRequest
    // can fire for the same callback URL — only process the first one.
    if (oauthExchangeInProgress.current) return;
    oauthExchangeInProgress.current = true;

    console.log("[OAuth] handleOAuthSuccess called, url prefix:", callbackUrl.substring(0, 60));
    setOauthUrl(null);
    setGoogleLoading(true);
    setErrorMsg("");

    try {
      // Parse the callback URL to detect PKCE (code in query) vs Implicit flow (token in hash)
      const hashFragment = callbackUrl.includes('#') ? callbackUrl.split('#')[1] : '';
      const hashParams = new URLSearchParams(hashFragment);
      const accessToken = hashParams.get('access_token');
      const refreshToken = hashParams.get('refresh_token');

      let session: any = null;

      if (accessToken) {
        // ── IMPLICIT FLOW: Supabase returned tokens directly in URL hash ──
        // This happens when the Supabase project uses implicit grant (not PKCE).
        // Use setSession to establish the session from the tokens.
        console.log("[OAuth] Implicit flow detected — calling setSession...");
        const { data, error } = await supabase.auth.setSession({
          access_token: accessToken,
          refresh_token: refreshToken ?? '',
        });
        if (error) {
          console.log("[OAuth] setSession ERROR:", error.message);
          setErrorMsg(error.message || "Google sign-in failed. Please try again.");
          return;
        }
        session = data.session;
      } else {
        // ── PKCE FLOW: Supabase returned a code in the URL query ──
        console.log("[OAuth] PKCE flow detected — calling exchangeCodeForSession...");
        const { data, error } = await supabase.auth.exchangeCodeForSession(callbackUrl);
        if (error) {
          console.log("[OAuth] exchangeCodeForSession ERROR:", error.message, error.status);
          setErrorMsg(error.message || "Google sign-in failed. Please try again.");
          return;
        }
        session = data.session;
      }

      if (!session) {
        console.log("[OAuth] no session returned");
        setErrorMsg("Sign-in completed but no session was returned. Please try again.");
        return;
      }
      const data = { session };
      console.log("[OAuth] session established, user:", data.session.user?.email);

      // Check backend to determine if role selection needed
      try {
        console.log("[OAuth] calling checkAuthState...");
        const meData = await checkAuthState(data.session.access_token);
        console.log("[OAuth] checkAuthState:", JSON.stringify({ needs_role: meData.needs_role_selection, role: meData.role }));
        if (meData.needs_role_selection) {
          console.log("[OAuth] routing to role-select");
          router.replace("/auth/role-select" as any);
        } else {
          console.log("[OAuth] routing to /(tabs)");
          router.replace("/(tabs)");
        }
      } catch (e2: any) {
        console.log("[OAuth] checkAuthState failed:", e2?.message, "→ defaulting to /(tabs)");
        router.replace("/(tabs)");
      }
    } catch (e: any) {
      const msg: string = e?.message ?? "Google sign-in failed.";
      console.log("[OAuth] OUTER catch:", msg);
      if (msg.includes("invalid") || msg.includes("expired")) {
        setErrorMsg("Sign-in session expired. Please try signing in again.");
      } else {
        setErrorMsg(msg);
      }
    } finally {
      setGoogleLoading(false);
      oauthExchangeInProgress.current = false;
    }
  }

  return (
    <>
      {oauthUrl && (
        <GoogleOAuthWebView
          url={oauthUrl}
          redirectUri={oauthRedirectUri}
          onSuccess={handleOAuthSuccess}
          onCancel={() => { setOauthUrl(null); setGoogleLoading(false); }}
        />
      )}
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }} edges={["top", "bottom"]}>
      <StatusBar style={colors.statusBar} />
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : "height"}>
        <ScrollView
          contentContainerStyle={[s.container, { backgroundColor: colors.bg }]}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
        >
          <Image source={require("../../assets/logo.png")} style={s.logo} resizeMode="contain" />

          <Text style={[s.taglineHero, { color: colors.text }]}>Learn smarter with AI.</Text>
          <Text style={[s.tagline, { color: colors.textMuted }]}>
            Personalized CBSE preparation with AI-powered lessons, mock tests, analytics and doubt solving. Class 5–12.
          </Text>

          {/* Google Sign-In */}
          <TouchableOpacity
            style={[s.googleBtn, { backgroundColor: colors.googleBtnBg, borderColor: colors.googleBtnBorder }]}
            onPress={handleGoogleLogin}
            disabled={googleLoading || loading}
          >
            {googleLoading ? (
              <ActivityIndicator color={colors.textMuted} size="small" />
            ) : (
              <>
                <Image source={require("../../assets/google-logo.png")} style={{ width: 22, height: 22 }} resizeMode="contain" />
                <Text style={[s.googleBtnTxt, { color: colors.googleBtnText }]}>Sign in with Google</Text>
              </>
            )}
          </TouchableOpacity>

          {/* Divider */}
          <View style={s.dividerRow}>
            <View style={[s.dividerLine, { backgroundColor: colors.divider }]} />
            <Text style={[s.dividerTxt, { color: colors.textMuted }]}>or sign in with email</Text>
            <View style={[s.dividerLine, { backgroundColor: colors.divider }]} />
          </View>

          {/* Email / password */}
          <View style={{ width: "100%", maxWidth: 400 }}>
            <Text style={[s.label, { color: colors.textSubtle }]}>Email or Username</Text>
            <TextInput
              style={[s.input, { backgroundColor: colors.surface, borderColor: colors.borderInput, color: colors.text }]}
              placeholder="your@email.com or username" placeholderTextColor={colors.textMuted}
              value={email} onChangeText={setEmail} keyboardType="email-address" autoCapitalize="none" autoCorrect={false}
            />
            <Text style={[s.label, { color: colors.textSubtle }]}>Password</Text>
            <View style={[s.inputRow, { backgroundColor: colors.surface, borderColor: colors.borderInput }]}>
              <TextInput
                style={[s.inputInner, { color: colors.text }]}
                placeholder="Password" placeholderTextColor={colors.textMuted}
                value={password} onChangeText={setPassword}
                secureTextEntry={!showPassword}
              />
              <TouchableOpacity onPress={() => setShowPassword(v => !v)} style={s.eyeBtn}>
                <Feather name={showPassword ? "eye-off" : "eye"} size={20} color={colors.textMuted} />
              </TouchableOpacity>
            </View>
            {errorMsg ? (
              <View style={[s.errorBox, { backgroundColor: colors.errorBg }]}>
                <Text style={[s.errorText, { color: colors.errorText }]}>❌ {errorMsg}</Text>
              </View>
            ) : null}
            <TouchableOpacity style={s.btn} onPress={handleLogin} disabled={loading || googleLoading}>
              {loading ? <ActivityIndicator color="#fff" /> : <Text style={s.btnText}>Sign In</Text>}
            </TouchableOpacity>
          </View>

          <TouchableOpacity onPress={() => router.push("/auth/signup")} style={s.linkRow}>
            <Text style={[s.linkText, { color: colors.textMuted }]}>Don't have an account? </Text>
            <Text style={[s.linkText, { color: BRAND_COLOR, fontWeight: "700" }]}>Sign up free</Text>
          </TouchableOpacity>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
    </>
  );
}

const s = StyleSheet.create({
  container: { flexGrow: 1, alignItems: "center", justifyContent: "center", padding: 24, paddingTop: 40 },
  logo: { width: 120, height: 120, borderRadius: 26, marginBottom: 20 },
  taglineHero: { fontSize: 17, fontWeight: "600", textAlign: "center" },
  tagline: { fontSize: 13, marginTop: 6, marginBottom: 28, textAlign: "center", lineHeight: 20, maxWidth: 320 },
  googleBtn: {
    flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 10,
    width: "100%", maxWidth: 400,
    borderRadius: 28, paddingVertical: 14, paddingHorizontal: 24,
    borderWidth: 1, marginBottom: 20,
    shadowColor: "#000", shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.08, shadowRadius: 3,
    elevation: 2,
  },
  googleBtnTxt: { fontSize: 15, fontWeight: "500" },
  dividerRow: { flexDirection: "row", alignItems: "center", width: "100%", maxWidth: 400, marginBottom: 20, gap: 10 },
  dividerLine: { flex: 1, height: 1 },
  dividerTxt: { fontSize: 12, fontWeight: "500" },
  label: { fontSize: 13, fontWeight: "600", marginBottom: 6 },
  input: { borderWidth: 1.5, borderRadius: 12, padding: 14, marginBottom: 16, fontSize: 16 },
  inputRow: { flexDirection: "row", alignItems: "center", borderWidth: 1.5, borderRadius: 12, marginBottom: 16 },
  inputInner: { flex: 1, padding: 14, fontSize: 16 },
  eyeBtn: { padding: 14 },
  errorBox: { borderRadius: 10, padding: 12, marginBottom: 14 },
  errorText: { fontSize: 14 },
  btn: { backgroundColor: BRAND_COLOR, borderRadius: 12, padding: 16, alignItems: "center", marginTop: 4 },
  btnText: { color: "#fff", fontSize: 16, fontWeight: "700" },
  linkRow: { flexDirection: "row", marginTop: 24 },
  linkText: { fontSize: 14 },
});
