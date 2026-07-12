/**
 * MINIMAL TEST — no Supabase, no expo-secure-store, no native modules.
 * Just verifies that Expo Router + React Native renders on this device.
 * If this opens → problem is in expo-secure-store or Supabase client init.
 * If this crashes → problem is with basic Expo Router setup on this device.
 */
import { Slot } from "expo-router";
import { StatusBar } from "expo-status-bar";

export default function RootLayout() {
  return (
    <>
      <StatusBar style="auto" />
      <Slot />
    </>
  );
}
