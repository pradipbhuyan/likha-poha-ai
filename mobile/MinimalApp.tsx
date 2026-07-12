/**
 * BARE MINIMUM test component — no expo-router, no native modules.
 * Purple screen with "Hello" text. Tests if React Native itself works.
 */
import React from "react";
import { View, Text, StyleSheet } from "react-native";

export default function MinimalApp() {
  return (
    <View style={s.container}>
      <Text style={s.text}>📚 Likha Poha AI v9</Text>
      <Text style={s.sub}>React Native is working!</Text>
    </View>
  );
}

const s = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: "#6366f1",
  },
  text: { fontSize: 24, color: "#fff", fontWeight: "bold", marginBottom: 12 },
  sub: { fontSize: 16, color: "#e0e7ff" },
});
