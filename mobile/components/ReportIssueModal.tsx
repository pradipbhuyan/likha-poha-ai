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

// Grouped so reporters get precise, friendly options instead of everything
// being forced into a vague "Other" bucket.
const ISSUE_TYPE_GROUPS: { label: string; items: { key: string; label: string }[] }[] = [
  {
    label: "📚 Content & Learning",
    items: [
      { key: "content_issue",      label: "Wrong Content" },
      { key: "wrong_explanation",  label: "Wrong Explanation" },
      { key: "missing_section",    label: "Missing Section" },
      { key: "wrong_formula",      label: "Wrong Formula" },
      { key: "wrong_answer",       label: "Wrong Answer" },
      { key: "translation_language", label: "Wrong Language" },
      { key: "audio_video_issue",  label: "Audio/Video Issue" },
    ],
  },
  {
    label: "⚙️ Technical",
    items: [
      { key: "broken_page",        label: "Broken Screen" },
      { key: "app_crash",          label: "App Crash / Froze" },
      { key: "slow_performance",   label: "Slow / Lagging" },
      { key: "sync_progress",      label: "Progress Not Saving" },
      { key: "notification_issue", label: "Notification Problem" },
      { key: "download_issue",     label: "Download / Offline" },
    ],
  },
  {
    label: "🔐 Account & Billing",
    items: [
      { key: "login_issue",        label: "Login Issue" },
      { key: "payment_billing",    label: "Payment / Subscription" },
    ],
  },
  {
    label: "💡 Other",
    items: [
      { key: "accessibility_issue", label: "Accessibility" },
      { key: "feature_request",     label: "Feature Request" },
      { key: "other",               label: "Something Else" },
    ],
  },
];

const SEVERITIES = [
  { key: "low",      label: "Low",      color: "#16a34a" },
  { key: "medium",   label: "Medium",   color: "#d97706" },
  { key: "high",     label: "High",     color: "#dc2626" },
  { key: "critical", label: "Critical", color: "#7c3aed" },
];

const REPRODUCIBILITY = [
  { key: "always",    label: "Every time" },
  { key: "sometimes", label: "Sometimes" },
  { key: "rarely",    label: "Rarely" },
  { key: "once",      label: "Just once" },
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
  const [reproducibility, setReproducibility] = useState("");
  const [title, setTitle]         = useState("");
  const [description, setDescription] = useState("");
  const [stepsToReproduce, setStepsToReproduce] = useState("");
  const [expectedBehavior, setExpectedBehavior] = useState("");
  const [actualBehavior, setActualBehavior]     = useState("");
  const [submitting, setSubmitting]   = useState(false);

  const { width, height } = Dimensions.get("window");

  function resetForm() {
    setTitle(""); setDescription(""); setIssueType("broken_page"); setSeverity("medium");
    setReproducibility(""); setStepsToReproduce(""); setExpectedBehavior(""); setActualBehavior("");
  }

  async function handleSubmit() {
    if (!description.trim() || description.trim().length < 10) {
      Alert.alert("Description too short", "Please describe the issue in at least 10 characters.");
      return;
    }

    setSubmitting(true);
    try {
      const deviceInfo = `${Platform.OS === "ios" ? "iOS" : "Android"} ${Platform.Version}`;
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
        steps_to_reproduce: stepsToReproduce.trim() || undefined,
        expected_behavior:  expectedBehavior.trim() || undefined,
        actual_behavior:    actualBehavior.trim() || undefined,
        reproducibility:    reproducibility || undefined,
        route:       `mobile/${currentScreen}`,
        app_version: APP_VERSION,
        device_info: deviceInfo,
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
        resetForm();
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
          <Text style={s.label}>What kind of issue is it?</Text>
          {ISSUE_TYPE_GROUPS.map(group => (
            <View key={group.label} style={{ marginBottom: 4 }}>
              <Text style={s.groupLabel}>{group.label}</Text>
              <View style={s.chipGrid}>
                {group.items.map(t => (
                  <TouchableOpacity
                    key={t.key}
                    style={[s.chip, issueType === t.key && s.chipActive]}
                    onPress={() => setIssueType(t.key)}>
                    <Text style={[s.chipText, issueType === t.key && s.chipTextActive]}>{t.label}</Text>
                  </TouchableOpacity>
                ))}
              </View>
            </View>
          ))}

          {/* Severity */}
          <Text style={s.label}>How bad is it?</Text>
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

          {/* Reproducibility */}
          <Text style={s.label}>How often does this happen? <Text style={s.optional}>(optional)</Text></Text>
          <View style={s.chipRow}>
            {REPRODUCIBILITY.map(r => (
              <TouchableOpacity
                key={r.key}
                style={[s.chip, reproducibility === r.key && s.chipActive]}
                onPress={() => setReproducibility(prev => prev === r.key ? "" : r.key)}>
                <Text style={[s.chipText, reproducibility === r.key && s.chipTextActive]}>{r.label}</Text>
              </TouchableOpacity>
            ))}
          </View>

          {/* Title (optional) */}
          <Text style={s.label}>Short summary <Text style={s.optional}>(optional)</Text></Text>
          <TextInput
            style={s.input}
            placeholder="e.g. Submit button does nothing on Mock Test"
            placeholderTextColor="#9ca3af"
            value={title}
            onChangeText={setTitle}
            maxLength={120}
          />

          {/* Description */}
          <Text style={s.label}>What happened? <Text style={s.required}>*</Text></Text>
          <TextInput
            style={[s.input, s.textarea]}
            placeholder="Describe what you found..."
            placeholderTextColor="#9ca3af"
            value={description}
            onChangeText={setDescription}
            multiline
            numberOfLines={4}
            textAlignVertical="top"
            maxLength={2000}
          />
          <Text style={s.charCount}>{description.length}/2000</Text>

          {/* Help us fix it faster */}
          <View style={s.helpBox}>
            <Text style={s.helpTitle}>🔍 Help us fix it faster</Text>
            <Text style={s.helpSubtitle}>Optional, but this is what lets us close your report without follow-up questions.</Text>

            <Text style={s.label}>Steps to reproduce</Text>
            <TextInput
              style={[s.input, s.textareaSmall]}
              placeholder={"1. Go to...\n2. Tap...\n3. See the problem"}
              placeholderTextColor="#9ca3af"
              value={stepsToReproduce}
              onChangeText={setStepsToReproduce}
              multiline
              numberOfLines={3}
              textAlignVertical="top"
              maxLength={1500}
            />

            <Text style={s.label}>What did you expect?</Text>
            <TextInput
              style={[s.input, s.textareaSmall]}
              placeholder="e.g. The quiz should submit"
              placeholderTextColor="#9ca3af"
              value={expectedBehavior}
              onChangeText={setExpectedBehavior}
              multiline
              numberOfLines={2}
              textAlignVertical="top"
              maxLength={1000}
            />

            <Text style={s.label}>What actually happened?</Text>
            <TextInput
              style={[s.input, s.textareaSmall]}
              placeholder="e.g. Nothing happens when I tap Submit"
              placeholderTextColor="#9ca3af"
              value={actualBehavior}
              onChangeText={setActualBehavior}
              multiline
              numberOfLines={2}
              textAlignVertical="top"
              maxLength={1000}
            />
          </View>

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
  groupLabel: { fontSize: 11, fontWeight: "700", color: "#9ca3af", marginBottom: 6, marginTop: 8 },
  optional: { fontWeight: "400", textTransform: "none", color: "#9ca3af" },
  required: { color: "#dc2626" },
  chipGrid: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginBottom: 4 },
  chipRow: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  chip: { paddingHorizontal: 12, paddingVertical: 7, borderRadius: 99, borderWidth: 1.5, borderColor: "#d1d5db", backgroundColor: "#fff" },
  chipActive: { borderColor: BRAND_COLOR, backgroundColor: "rgba(99,102,241,.08)" },
  chipText: { fontSize: 12, fontWeight: "600", color: "#374151" },
  chipTextActive: { color: BRAND_COLOR },
  input: { backgroundColor: "#f8fafc", borderWidth: 1.5, borderColor: "#e2e8f0", borderRadius: 10, padding: 12, fontSize: 14, color: "#111827" },
  textarea: { minHeight: 110, lineHeight: 20 },
  textareaSmall: { minHeight: 64, lineHeight: 20 },
  charCount: { fontSize: 11, color: "#9ca3af", textAlign: "right", marginTop: 4 },
  helpBox: { backgroundColor: "#f8fafc", borderRadius: 12, padding: 14, marginTop: 20 },
  helpTitle: { fontSize: 13, fontWeight: "800", color: BRAND_COLOR },
  helpSubtitle: { fontSize: 11, color: "#94a3b8", marginTop: 2, lineHeight: 15 },
  submitBtn: { backgroundColor: BRAND_COLOR, borderRadius: 12, padding: 15, alignItems: "center", marginTop: 20 },
  submitBtnText: { color: "#fff", fontWeight: "700", fontSize: 16 },
});
