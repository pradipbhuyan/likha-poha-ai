import { useEffect, useState } from "react";
import { View, Text, Image, TouchableOpacity } from "react-native";
import { Tabs, useRouter, useSegments } from "expo-router";
import { Feather } from "@expo/vector-icons";
import { BRAND_COLOR } from "../../constants";
import { authFetch } from "../../lib/authFetch";
import ReportIssueModal from "../../components/ReportIssueModal";

// Professional Feather vector icon tab component
// Feather is the upstream of Lucide — identical icon designs
function TabIcon({ name, focused }: { name: React.ComponentProps<typeof Feather>["name"]; focused: boolean }) {
  return <Feather name={name} size={22} color={focused ? BRAND_COLOR : "#9ca3af"} />;
}

function HeaderRight() {
  const router = useRouter();
  return (
    <TouchableOpacity
      onPress={() => router.navigate("/(tabs)/account" as any)}
      style={{ marginRight: 16, padding: 6, borderRadius: 20, backgroundColor: "rgba(99,102,241,.08)" }}
    >
      <Feather name="user" size={20} color={BRAND_COLOR} />
    </TouchableOpacity>
  );
}

function HeaderLogo() {
  return (
    <View style={{ flexDirection: "row", alignItems: "center", gap: 10 }}>
      <Image
        source={require("../../assets/logo.png")}
        style={{ width: 64, height: 64, borderRadius: 14 }}
        resizeMode="contain"
      />
      <View>
        <Text style={{ fontSize: 18, fontWeight: "700", color: "#374151", letterSpacing: -0.3 }}>
          Your Personal Tutor
        </Text>
      </View>
    </View>
  );
}

export default function TabsLayout() {
  const [canReportIssues, setCanReportIssues] = useState(false);
  const [reportOpen, setReportOpen] = useState(false);
  const segments = useSegments();

  // Current screen = last segment (e.g. "lessons", "doubt", "formula")
  const currentScreen = segments[segments.length - 1] || "home";

  useEffect(() => {
    authFetch("/api/auth/me").then((me: any) => {
      setCanReportIssues(!!me?.can_report_issues);
    }).catch(() => {});
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <>
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: BRAND_COLOR,
        tabBarInactiveTintColor: "#9ca3af",
        tabBarStyle: {
          borderTopColor: "#e5e7eb",
          backgroundColor: "#fff",
          justifyContent: "space-evenly" as const,
          paddingHorizontal: 0,
        },
        tabBarItemStyle: {
          flex: 1,
        },
        headerStyle: { backgroundColor: "#fff" },
        headerTintColor: "#111827",
        headerTitleStyle: { fontWeight: "700" },
        headerLeft: () => <View style={{ marginLeft: 16 }}><HeaderLogo /></View>,
        headerTitle: () => null,
        headerRight: () => <HeaderRight />,
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: "Home",
          tabBarLabel: "Home",
          tabBarIcon: ({ focused }) => <TabIcon name="home" focused={focused} />,
        }}
      />
      <Tabs.Screen
        name="lessons"
        options={{
          title: "Lessons",
          tabBarLabel: "Lessons",
          tabBarIcon: ({ focused }) => <TabIcon name="book-open" focused={focused} />,
        }}
      />
      <Tabs.Screen
        name="mocktest"
        options={{
          title: "Mock Test",
          tabBarLabel: "Mock Test",
          tabBarIcon: ({ focused }) => <TabIcon name="edit-3" focused={focused} />,
        }}
      />
      <Tabs.Screen
        name="doubt"
        options={{
          title: "Ask Doubt",
          tabBarLabel: "Ask AI",
          tabBarIcon: ({ focused }) => <TabIcon name="message-circle" focused={focused} />,
        }}
      />
      <Tabs.Screen
        name="formula"
        options={{
          title: "Formulas & Concepts",
          tabBarLabel: "Formula",
          tabBarIcon: ({ focused }) => <TabIcon name="grid" focused={focused} />,
        }}
      />
      <Tabs.Screen
        name="account"
        options={{
          title: "Account",
          tabBarButton: () => null,
          tabBarItemStyle: { display: "none" },
        }}
      />
      <Tabs.Screen
        name="analytics"
        options={{
          title: "Analytics",
          tabBarButton: () => null,
          tabBarItemStyle: { display: "none" },
        }}
      />
      <Tabs.Screen
        name="examprep"
        options={{
          title: "Exam Prep",
          tabBarButton: () => null,
          tabBarItemStyle: { display: "none" },
        }}
      />
      <Tabs.Screen
        name="learn"
        options={{
          title: "Learn More",
          tabBarLabel: "Learn More",
          tabBarIcon: ({ focused }) => <TabIcon name="external-link" focused={focused} />,
        }}
      />
      <Tabs.Screen
        name="boardpapers"
        options={{
          title: "Board Papers",
          tabBarLabel: "Papers",
          tabBarIcon: ({ focused }) => <TabIcon name="clipboard" focused={focused} />,
        }}
      />
      <Tabs.Screen
        name="exemplar"
        options={{
          title: "Exemplar",
          tabBarButton: () => null,
          tabBarItemStyle: { display: "none" },
        }}
      />
    </Tabs>

    {/* Floating Report Issue button — only for authorized users */}
    {canReportIssues && (
      <>
        <TouchableOpacity
          onPress={() => setReportOpen(true)}
          style={{
            position: "absolute", bottom: 88, right: 16, zIndex: 900,
            backgroundColor: "#6366f1", borderRadius: 24,
            paddingHorizontal: 14, paddingVertical: 9,
            flexDirection: "row", alignItems: "center", gap: 6,
            shadowColor: "#6366f1", shadowOffset: { width: 0, height: 3 },
            shadowOpacity: 0.4, shadowRadius: 8, elevation: 6,
          }}>
          <Feather name="alert-circle" size={15} color="#fff" />
          <Text style={{ color: "#fff", fontSize: 12, fontWeight: "700" }}>Report Issue</Text>
        </TouchableOpacity>

        <ReportIssueModal
          visible={reportOpen}
          onClose={() => setReportOpen(false)}
          currentScreen={currentScreen}
        />
      </>
    )}
    </>
  );
}
