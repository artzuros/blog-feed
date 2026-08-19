import { InstrumentSerif_400Regular } from '@expo-google-fonts/instrument-serif';
import {
  WorkSans_400Regular,
  WorkSans_500Medium,
  WorkSans_600SemiBold,
  WorkSans_700Bold,
} from '@expo-google-fonts/work-sans';
import { useFonts } from 'expo-font';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useColorScheme } from 'react-native';
import { fonts, useTheme } from '../lib/theme';

export default function RootLayout() {
  const [fontsLoaded] = useFonts({
    InstrumentSerif_400Regular,
    WorkSans_400Regular,
    WorkSans_500Medium,
    WorkSans_600SemiBold,
    WorkSans_700Bold,
  });
  const c = useTheme();
  const scheme = useColorScheme();

  // Hold rendering until the fonts are in memory — otherwise text flashes in
  // the wrong face before the fonts load.
  if (!fontsLoaded) return null;

  return (
    <>
      <StatusBar style={scheme === 'dark' ? 'light' : 'dark'} />
      <Stack
        screenOptions={{
          headerTintColor: c.primary,
          headerTitleStyle: { color: c.text, fontFamily: fonts.serif },
          headerStyle: { backgroundColor: c.bg },
          headerShadowVisible: false,
          contentStyle: { backgroundColor: c.bg },
        }}
      >
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
        <Stack.Screen name="article/[id]" options={{ title: 'Article' }} />
      </Stack>
    </>
  );
}
