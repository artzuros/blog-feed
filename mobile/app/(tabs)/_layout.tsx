import { Ionicons } from '@expo/vector-icons';
import { Tabs } from 'expo-router';
import { fonts, useTheme } from '../../lib/theme';

export default function TabsLayout() {
  const c = useTheme();
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: c.primary,
        tabBarInactiveTintColor: c.textMuted,
        tabBarLabelStyle: { fontFamily: fonts.sansMedium, fontSize: 11 },
        tabBarStyle: {
          backgroundColor: c.surface,
          borderTopColor: c.border,
        },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: 'Search',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="search" color={color} size={size} />
          ),
        }}
      />
      <Tabs.Screen
        name="browse"
        options={{
          title: 'Browse',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="newspaper-outline" color={color} size={size} />
          ),
        }}
      />
    </Tabs>
  );
}
