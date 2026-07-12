/**
 * MINIMAL TEST SCREEN — pure React Native, no imports from lib/.
 * Verifies basic rendering works on this device.
 */
import { View, Text, StyleSheet } from "react-native";

export default function LoginScreen() {
  return (
    <View style={styles.container}>
      <Text style={styles.emoji}>📚</Text>
      <Text style={styles.title}>Likha Poha AI</Text>
      <Text style={styles.sub}>App is working! ✅</Text>
      <Text style={styles.note}>
        If you see this screen, the basic app works.{"\n"}
        The crash was in a native module.
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: "center", alignItems: "center", backgroundColor: "#f8fafc", padding: 24 },
  emoji: { fontSize: 60, marginBottom: 16 },
  title: { fontSize: 28, fontWeight: "800", color: "#6366f1", marginBottom: 8 },
  sub: { fontSize: 18, color: "#16a34a", fontWeight: "700", marginBottom: 20 },
  note: { fontSize: 14, color: "#6b7280", textAlign: "center", lineHeight: 22 },
});
