/**
 * ReportIssueModal.tsx — Mobile bug/issue reporter
 *
 * Mirrors the web ReportIssueModal but captures mobile-specific context:
 *  - Current screen (tab name from expo-router)
 *  - App version + build number from app.json
 *  - Platform (Android/iOS)
 *  - Screen dimensions
 *
 * Access control: only renders when canReportIssues=true (same permission as web).
 * Backend endpoint: POST /api/issues/report
 */
import { useState } from "react";
import {
  View, Text, TextInput, TouchableOpacity, Modal,
  ScrollView, StyleSheet, Dimensions, Platform, ActivityIndicator, Alert,
} from "react-native";
import { Feather } from "@expo/vector-icons";
import { authFetch } from "../lib/authFetch";
import { BRAND_COLOR } from "../constants";

// Get app version from app.json via Expo constants
let APP_VERSION = "v1.1.0";
let BUILD_NUMBER = "35";
try {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const Constants = require("expo-constants").default;
  APP_VERSION = Constants.expoConfig?.version || "v1.1.0";
  BUILD_NUMBER = String(Constants.expoConfig?.android?.versionCode || "35");
} catch { /* ignore */ }

const ISSUE_TYPES = [
  { key: "content_issue",     label: "Wrong Content" },
  { key: "wrong_explanation", label: "Wrong Explanation" },
  { key: "missing_section",   label: "Missing Section" },
  { key: "wrong_formula",     label: "Wrong Formula" },
  { key: "wrong_answer",      label: "Wrong Answer" },
  { key: "broken_page",       label: "App Crash / Broken Screen" },
  { key: "login_issue",       label: "Login Issue" },
  { key: "other",             label: "Other" },
];

const SEVERITIES = [
  { key: "low",      label: "Low",      color: "#16a34a" },
  { key: "medium",   label: "Medium",   color: "#d97706" },
  { key: "high",     label: "High",     color: "#dc2626" },
  { key: "critical", label: "Critical", color: "#7c3aed" },
];

interface Props {
  visible: boolean;
  onClose: () => void;
  currentScreen: string;   // e.g. "lessons", "doubt", "formula"
  grade?: string;
  subject?: string;
}

export default function ReportIssueModal({ visible, onClose, currentScreen, grade, subject }: Props) {
  const [issueType, setIssueType] = useState("broken_page");
  const [severity, setSeverity]   = useState("medium");
  const [title, setTitle]         = useState("");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting]   = useState(false);

  const { width, height } = Dimensions.get("window");

  async function handleSubmit() {
    if (!description.trim() || description.trim().length < 10) {
      Alert.alert("Description too short", "Please describe the issue in at least 10 characters.");
      return;
    }

    setSubmitting(true);
    try {
      const browserInfo = {
        platform: Platform.OS,           // "android" | "ios"
        appVersion: APP_VERSION,
        buildNumber: BUILD_NUMBER,
        currentScreen,                   // current tab/screen
        screenWidth: Math.round(width),
        screenHeight: Math.round(height),
        osVersion: String(Platform.Version),
        source: "mobile_app",
      };

      const payload: Record<string, unknown> = {
        issue_type:  issueType,
        severity,
        title:       title.trim() || undefined,
        description: description.trim(),
        route:       `mobile/${currentScreen}`,
        browser_info: browserInfo,
      };
      if (grade)   payload.grade   = grade;
      if (subject) payload.subject = subject;

      const res: any = await authFetch("/api/issues/report", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      if (res?.success || res?.defect_number) {
        Alert.alert(
          "Report Submitted ✅",
          `Issue reported${res.defect_number ? ` (${res.defect_number})` : ""}. Our team will review it.`,
          [{ text: "OK", onPress: onClose }]
        );
        setTitle(""); setDescription(""); setIssueType("broken_page"); setSeverity("medium");
      } else {
        Alert.alert("Error", res?.detail || "Could not submit report. Please try again.");
      }
    } catch (e: any) {
      Alert.alert("Error", e?.message || "Could not submit report.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal visible={visible} animationType="slide" presentationStyle="pageSheet" onRequestClose={onClose}>
      <View style={s.container}>
        {/* Header */}
        <View style={s.header}>
          <Text style={s.headerTitle}>🐛 Report an Issue</Text>
          <TouchableOpacity onPress={onClose} style={s.closeBtn}>
            <Feather name="x" size={22} color="#374151" />
          </TouchableOpacity>
        </View>

        {/* Context badge */}
        <View style={s.contextBadge}>
          <Feather name="info" size={12} color="#6366f1" />
          <Text style={s.contextText}>
            Screen: {currentScreen} · v{APP_VERSION} build {BUILD_NUMBER} · {Platform.OS}
          </Text>
        </View>

        <ScrollView style={s.body} keyboardShouldPersistTaps="handled">

          {/* Issue Type */}
          <Text style={s.label}>Issue Type</Text>
          <View style={s.chipGrid}>
            {ISSUE_TYPES.map(t => (
              <TouchableOpacity
                key={t.key}
                style={[s.chip, issueType === t.key && s.chipActive]}
                onPress={() => setIssueType(t.key)}>
                <Text style={[s.chipText, issueType === t.key && s.chipTextActive]}>{t.label}</Text>
              </TouchableOpacity>
            ))}
          </View>

          {/* Severity */}
          <Text style={s.label}>Severity</Text>
          <View style={s.chipRow}>
            {SEVERITIES.map(sv => (
              <TouchableOpacity
                key={sv.key}
                style={[s.chip, severity === sv.key && { borderColor: sv.color, backgroundColor: sv.color + "15" }]}
                onPress={() => setSeverity(sv.key)}>
                <Text style={[s.chipText, severity === sv.key && { color: sv.color }]}>{sv.label}</Text>
              </TouchableOpacity>
            ))}
          </View>

          {/* Title (optional) */}
          <Text style={s.label}>Title <Text style={s.optional}>(optional)</Text></Text>
          <TextInput
            style={s.input}
            placeholder="Short summary of the issue"
            placeholderTextColor="#9ca3af"
            value={title}
            onChangeText={setTitle}
            maxLength={120}
          />

          {/* Description */}
          <Text style={s.label}>Description <Text style={s.required}>*</Text></Text>
          <TextInput
            style={[s.input, s.textarea]}
            placeholder="Describe what happened, what you expected, and steps to reproduce..."
            placeholderTextColor="#9ca3af"
            value={description}
            onChangeText={setDescription}
            multiline
            numberOfLines={5}
            textAlignVertical="top"
            maxLength={2000}
          />
          <Text style={s.charCount}>{description.length}/2000</Text>

          {/* Submit */}
          <TouchableOpacity
            style={[s.submitBtn, submitting && { opacity: 0.6 }]}
            onPress={handleSubmit}
            disabled={submitting}>
            {submitting ? (
              <ActivityIndicator color="#fff" size="small" />
            ) : (
              <Text style={s.submitBtnText}>Submit Report</Text>
            )}
          </TouchableOpacity>

          <View style={{ height: 40 }} />
        </ScrollView>
      </View>
    </Modal>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#fff" },
  header: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingHorizontal: 20, paddingTop: 20, paddingBottom: 12, borderBottomWidth: 1, borderBottomColor: "#f3f4f6" },
  headerTitle: { fontSize: 17, fontWeight: "800", color: "#111827" },
  closeBtn: { padding: 6, borderRadius: 8, backgroundColor: "#f9fafb" },
  contextBadge: { flexDirection: "row", alignItems: "center", gap: 6, backgroundColor: "rgba(99,102,241,.06)", borderRadius: 8, paddingHorizontal: 12, paddingVertical: 6, marginHorizontal: 16, marginTop: 12, borderWidth: 1, borderColor: "rgba(99,102,241,.15)" },
  contextText: { fontSize: 11, color: "#6366f1", fontWeight: "600", flex: 1 },
  body: { flex: 1, paddingHorizontal: 16, paddingTop: 16 },
  label: { fontSize: 12, fontWeight: "700", color: "#374151", textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 8, marginTop: 16 },
  optional: { fontWeight: "400", textTransform: "none", color: "#9ca3af" },
  required: { color: "#dc2626" },
  chipGrid: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  chipRow: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  chip: { paddingHorizontal: 12, paddingVertical: 7, borderRadius: 99, borderWidth: 1.5, borderColor: "#d1d5db", backgroundColor: "#fff" },
  chipActive: { borderColor: BRAND_COLOR, backgroundColor: "rgba(99,102,241,.08)" },
  chipText: { fontSize: 12, fontWeight: "600", color: "#374151" },
  chipTextActive: { color: BRAND_COLOR },
  input: { backgroundColor: "#f8fafc", borderWidth: 1.5, borderColor: "#e2e8f0", borderRadius: 10, padding: 12, fontSize: 14, color: "#111827" },
  textarea: { minHeight: 110, lineHeight: 20 },
  charCount: { fontSize: 11, color: "#9ca3af", textAlign: "right", marginTop: 4 },
  submitBtn: { backgroundColor: BRAND_COLOR, borderRadius: 12, padding: 15, alignItems: "center", marginTop: 20 },
  submitBtnText: { color: "#fff", fontWeight: "700", fontSize: 16 },
});
