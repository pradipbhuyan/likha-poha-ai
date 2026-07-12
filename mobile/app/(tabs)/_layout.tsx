import { Text } from "react-native";
import { Tabs } from "expo-router";
import type { ColorValue } from "react-native";
import { BRAND_COLOR } from "../../constants";

function TabIcon({ icon, focused }: { icon: string; focused: boolean }) {
  return <Text style={{ fontSize: 20, opacity: focused ? 1 : 0.45 }}>{icon}</Text>;
}

export default function TabsLayout() {
  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: BRAND_COLOR,
        tabBarInactiveTintColor: "#9ca3af",
        tabBarStyle: { borderTopColor: "#e5e7eb" },
        headerStyle: { backgroundColor: "#fff" },
        headerTintColor: "#111827",
        headerTitleStyle: { fontWeight: "700" },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{ title: "Home", tabBarIcon: ({ focused }) => <TabIcon icon="🏠" focused={focused} /> }}
      />
      <Tabs.Screen
        name="lessons"
        options={{ title: "Lessons", tabBarIcon: ({ focused }) => <TabIcon icon="📚" focused={focused} /> }}
      />
      <Tabs.Screen
        name="mocktest"
        options={{ title: "Mock Test", tabBarIcon: ({ focused }) => <TabIcon icon="✍️" focused={focused} /> }}
      />
      <Tabs.Screen
        name="account"
        options={{ title: "Account", tabBarIcon: ({ focused }) => <TabIcon icon="👤" focused={focused} /> }}
      />
    </Tabs>
  );
}
