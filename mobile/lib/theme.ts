/**
 * Likha Poha AI — Dark / Light theme tokens.
 *
 * Usage in any component:
 *   const { colors, isDark } = useTheme();
 *   <View style={{ backgroundColor: colors.bg }}>
 *
 * Colors follow the CODEX rule:
 *   inline-style fallbacks MUST be light-mode defaults (never dark).
 */
import { useColorScheme } from "react-native";
import { BRAND_COLOR } from "../constants";

export const light = {
  bg:           "#f8fafc",
  surface:      "#ffffff",
  surface2:     "#f1f5f9",
  border:       "#e5e7eb",
  borderInput:  "#d1d5db",
  text:         "#111827",
  textSubtle:   "#374151",
  textMuted:    "#6b7280",
  brand:        BRAND_COLOR,
  brandLight:   "#eef2ff",
  errorBg:      "#fef2f2",
  errorText:    "#dc2626",
  divider:      "#e5e7eb",
  // Google button
  googleBtnBg:  "#ffffff",
  googleBtnBorder: "#e0e0e0",
  googleBtnText:  "#3c4043",
  // Status-bar style
  statusBar:    "dark" as const,
};

export const dark = {
  bg:           "#0f172a",
  surface:      "#1e293b",
  surface2:     "#162032",
  border:       "#334155",
  borderInput:  "#475569",
  text:         "#f1f5f9",
  textSubtle:   "#cbd5e1",
  textMuted:    "#94a3b8",
  brand:        BRAND_COLOR,
  brandLight:   "rgba(99,102,241,0.18)",
  errorBg:      "rgba(239,68,68,0.12)",
  errorText:    "#f87171",
  divider:      "#334155",
  // Google button — dark bg, white text
  googleBtnBg:  "#1e293b",
  googleBtnBorder: "#475569",
  googleBtnText:  "#f1f5f9",
  // Status-bar style
  statusBar:    "light" as const,
};

export type ThemeColors = Omit<typeof light, "statusBar"> & { statusBar: "dark" | "light" };

export function useTheme(): { colors: ThemeColors; isDark: boolean } {
  const scheme = useColorScheme();
  const isDark = scheme === "dark";
  return { colors: isDark ? dark : light, isDark };
}
