/**
 * Supabase client for the Likha Poha AI mobile app.
 *
 * Key differences from the web client:
 * - detectSessionInUrl: false  (Expo handles deep links differently from browsers)
 * - storage: expo-secure-store  (replaces localStorage)
 * - autoRefreshToken: true      (keeps JWT fresh automatically)
 */
import { createClient } from "@supabase/supabase-js";
import * as SecureStore from "expo-secure-store";
import { SUPABASE_URL, SUPABASE_ANON_KEY } from "../constants";

/**
 * Robust storage adapter with in-memory fallback.
 *
 * expo-secure-store on Android emulators WITHOUT a screen lock/PIN can fail
 * silently because Android Keystore requires a secure lock screen. This causes
 * the PKCE code verifier to be lost, making exchangeCodeForSession fail.
 *
 * Fix: always write to memory cache first, then try SecureStore. On read,
 * return memory cache if SecureStore fails. Sessions persist within the app
 * session even if SecureStore is unavailable.
 */
const _memCache = new Map<string, string>();

const RobustStorageAdapter = {
  async getItem(key: string): Promise<string | null> {
    try {
      const val = await SecureStore.getItemAsync(key);
      if (val != null) return val;
    } catch { /* SecureStore unavailable */ }
    return _memCache.get(key) ?? null;
  },
  async setItem(key: string, value: string): Promise<void> {
    _memCache.set(key, value);
    try { await SecureStore.setItemAsync(key, value); } catch { /* ignore */ }
  },
  async removeItem(key: string): Promise<void> {
    _memCache.delete(key);
    try { await SecureStore.deleteItemAsync(key); } catch { /* ignore */ }
  },
};

export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
  auth: {
    storage: RobustStorageAdapter as any,
    autoRefreshToken: true,
    persistSession: true,
    detectSessionInUrl: false, // IMPORTANT: Expo handles OAuth deep links, not the browser
  },
});
