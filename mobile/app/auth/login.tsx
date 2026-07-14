/**
 * Login screen — email/password + Google OAuth.
 * Supports light and dark mode via useTheme().
 */
import { useState } from "react";
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
import { signInWithGoogle } from "../../lib/auth";
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
    // Detect when the OAuth callback redirects back to our app scheme
    if (navUrl.startsWith("likhapoha://") || navUrl.startsWith(redirectUri)) {
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
              if (req.url.startsWith("likhapoha://") || req.url.startsWith(redirectUri)) {
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

  async function handleLogin() {
    if (!email.trim() || !password) { setErrorMsg("Please enter your email or username and password."); return; }
    setLoading(true); setErrorMsg("");
    try {
      let loginEmail = email.trim().toLowerCase();

      // Username login — if input has no @, resolve to email via /api/auth/lookup-email
      if (!loginEmail.includes("@")) {
        const res = await fetch(`${API_BASE_URL}/api/auth/lookup-email/${encodeURIComponent(loginEmail)}`);
        if (!res.ok) {
          setErrorMsg("Username not found. Please check your username or use your email.");
          setLoading(false);
          return;
        }
        const data = await res.json();
        loginEmail = data.email;
      }

      const { error } = await supabase.auth.signInWithPassword({ email: loginEmail, password });
      if (error) setErrorMsg(error.message);
    } catch (e: any) { setErrorMsg(e?.message ?? "Login failed. Please try again."); }
    finally { setLoading(false); }
  }

  const [oauthUrl, setOauthUrl] = useState<string | null>(null);
  const [oauthRedirectUri, setOauthRedirectUri] = useState<string>("");

  async function handleGoogleLogin() {
    setGoogleLoading(true); setErrorMsg("");
    try {
      const { url, redirectUri, error } = await signInWithGoogle();
      if (error || !url) throw error ?? new Error("Could not start Google sign-in.");

      if (NativeWebView) {
        // Native APK build: use WebView modal — respects network_security_config.xml (Zscaler certs)
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
    setOauthUrl(null);
    try {
      const { error } = await supabase.auth.exchangeCodeForSession(callbackUrl);
      if (error) setErrorMsg(error.message);
      // On success _layout.tsx onAuthStateChange routes the user
    } catch (e: any) { setErrorMsg(e?.message ?? "Sign-in failed after OAuth."); }
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
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
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
            <TextInput
              style={[s.input, { backgroundColor: colors.surface, borderColor: colors.borderInput, color: colors.text }]}
              placeholder="Password" placeholderTextColor={colors.textMuted}
              value={password} onChangeText={setPassword} secureTextEntry
            />
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
  input: { borderWidth: 1, borderRadius: 12, padding: 14, marginBottom: 16, fontSize: 16 },
  errorBox: { borderRadius: 10, padding: 12, marginBottom: 14 },
  errorText: { fontSize: 14 },
  btn: { backgroundColor: BRAND_COLOR, borderRadius: 12, padding: 16, alignItems: "center", marginTop: 4 },
  btnText: { color: "#fff", fontSize: 16, fontWeight: "700" },
  linkRow: { flexDirection: "row", marginTop: 24 },
  linkText: { fontSize: 14 },
});
