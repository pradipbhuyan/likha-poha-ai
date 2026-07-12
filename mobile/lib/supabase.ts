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

/** Expo SecureStore adapter — replaces browser localStorage. */
const ExpoSecureStoreAdapter = {
  getItem: (key: string) => SecureStore.getItemAsync(key),
  setItem: (key: string, value: string) => SecureStore.setItemAsync(key, value),
  removeItem: (key: string) => SecureStore.deleteItemAsync(key),
};

export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
  auth: {
    storage: ExpoSecureStoreAdapter as any,
    autoRefreshToken: true,
    persistSession: true,
    detectSessionInUrl: false, // IMPORTANT: Expo handles OAuth deep links, not the browser
  },
});
