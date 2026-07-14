/**
 * AppHeader — shared top bar matching the tab screen header.
 * Shows the Likha Poha AI logo + brand name + tagline.
 * Used on non-tab screens (learn.tsx, exemplar.tsx, etc.)
 * to maintain brand consistency across all screens.
 */
import { View, Text, Image, TouchableOpacity, StyleSheet } from "react-native";
import { Feather } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import { BRAND_COLOR } from "../constants";

interface AppHeaderProps {
  showBack?: boolean;
}

export default function AppHeader({ showBack = true }: AppHeaderProps) {
  const router = useRouter();
  return (
    <View style={s.container}>
      {showBack ? (
        <TouchableOpacity style={s.backBtn} onPress={() => router.back()}>
          <Feather name="arrow-left" size={20} color={BRAND_COLOR} />
        </TouchableOpacity>
      ) : (
        <View style={s.backPlaceholder} />
      )}
      <View style={s.logoRow}>
        <Image
          source={require("../assets/logo.png")}
          style={s.logo}
          resizeMode="contain"
        />
        <View>
          <Text style={s.tagline}>Your Personal Tutor</Text>
        </View>
      </View>
    </View>
  );
}

const s = StyleSheet.create({
  container: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 16,
    paddingVertical: 10,
    backgroundColor: "#fff",
    borderBottomWidth: 1,
    borderBottomColor: "#e5e7eb",
  },
  backBtn: {
    padding: 8,
    borderRadius: 8,
    backgroundColor: "rgba(99,102,241,.08)",
    marginRight: 12,
  },
  backPlaceholder: { width: 36, marginRight: 12 },
  logoRow: { flexDirection: "row", alignItems: "center", gap: 10 },
  logo: { width: 64, height: 64, borderRadius: 14 },
  tagline: { fontSize: 18, fontWeight: "700", color: "#374151", letterSpacing: -0.3 },
});
