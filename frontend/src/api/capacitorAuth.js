import { Capacitor } from "@capacitor/core";
import { Browser } from "@capacitor/browser";
import { App } from "@capacitor/app";
import { supabase } from "./supabaseClient";

// Must also be registered as a Redirect URL in the Supabase dashboard
// (Authentication → URL Configuration) and matches the intent-filter
// scheme added to android/app/src/main/AndroidManifest.xml.
const NATIVE_REDIRECT_URL = "likhapohaweb://auth-callback";

export const isNativePlatform = () => Capacitor.isNativePlatform();

/**
 * Opens Google OAuth in the system in-app browser instead of navigating the
 * WebView. supabaseClient.js uses the default implicit flow, so the redirect
 * carries access_token/refresh_token in the URL hash — registerNativeAuthListener
 * picks that up via the appUrlOpen deep link and calls setSession(), which is
 * the same mechanism the existing web onAuthStateChange listener expects.
 */
export async function signInWithGoogleNative() {
  const { data, error } = await supabase.auth.signInWithOAuth({
    provider: "google",
    options: {
      redirectTo: NATIVE_REDIRECT_URL,
      skipBrowserRedirect: true,
      queryParams: { access_type: "offline", prompt: "select_account" },
    },
  });
  if (error) throw error;
  await Browser.open({ url: data.url });
}

let listenerRegistered = false;

/** Call once at app bootstrap (native only) to catch the OAuth deep-link callback. */
export function registerNativeAuthListener() {
  if (listenerRegistered || !isNativePlatform()) return;
  listenerRegistered = true;

  App.addListener("appUrlOpen", async ({ url }) => {
    if (!url.startsWith(NATIVE_REDIRECT_URL)) return;

    try {
      await Browser.close();
    } catch {
      /* already closed */
    }

    const hash = url.includes("#") ? url.split("#")[1] : "";
    const params = new URLSearchParams(hash);
    const access_token = params.get("access_token");
    const refresh_token = params.get("refresh_token");
    const errorDescription = params.get("error_description") || params.get("error");

    if (errorDescription) {
      console.error("Native Google sign-in failed:", errorDescription);
      return;
    }
    if (!access_token || !refresh_token) {
      console.error("Native Google sign-in: no tokens in callback URL");
      return;
    }

    const { error } = await supabase.auth.setSession({ access_token, refresh_token });
    if (error) console.error("Native Google sign-in: setSession failed", error);
  });
}
