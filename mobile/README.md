# Blog Feed — Mobile App

Expo (React Native) client for the [Blog Feed API](../README.md). Cross-platform (iOS + Android + web), one codebase.

The app queries the live API at `https://blog-feed-aws.pranav-bansal.com/api` — **it works out of the box, no backend needed.**

## Prerequisites

| Tool | Where needed |
| --- | --- |
| Node.js ≥ 22 | Both machines |
| Expo Go (App Store / Play Store) | Physical iPhone/Android for quick preview |
| Xcode + iOS Simulator | MacBook only — for native iOS simulator builds |
| Android Studio / emulator | Optional — for Android native builds |
| Apple Developer Program ($99/yr) | Only when shipping iOS to TestFlight/App Store |

> **Why this project is on Expo SDK 54:** the App Store / Play Store versions of
> **Expo Go only support SDK 54** (Apple has not approved newer Expo Go builds).
> A project on SDK 55+ **cannot** be opened in the store version of Expo Go on a
> physical phone — it shows *"Project is incompatible with this version of Expo Go."*
> Keep this app on SDK 54 as long as you rely on Expo Go for device preview.
> When you want SDK 55+, switch to a [development build](https://docs.expo.dev/develop/development-builds/introduction/)
> (`npx expo run:ios` on the MacBook), which does not use Expo Go at all.

## Quick start

```bash
cd mobile
npm install
npx expo start
```

Then pick a target:

- **iPhone (physical)** — install Expo Go, scan the QR code in the terminal (or press `s` to send a link).
- **iOS Simulator** (MacBook only) — press `i`.
- **Android emulator** — press `a`.
- **Web** — press `w` (great for a fast in-browser check).

## Running on your iPhone — which machine to use

Expo Go on the phone connects to the Metro dev server running on the **same machine as `npx expo start`**, over your local network. Two options:

### Option A — MacBook (recommended for iOS dev)

Your MacBook and iPhone are usually on the same Wi-Fi, so this is the most reliable path — and it's where all native iOS tooling lives.

```bash
git clone <repo> && cd <repo>/mobile
npm install
npx expo start
# scan the QR with the iPhone Camera app → opens in Expo Go
# or press `i` to launch the iOS Simulator (requires Xcode)
```

### Option B — this Linux server (where you are now)

The server can host Metro too — the iPhone just needs to reach it:

```bash
# from the blog-feed repo root on the server
cd mobile
npx expo start
```

- If the iPhone is on the **same LAN** as the server, the QR code works as-is.
- Not on the same network? Use a tunnel so the phone reaches the server over the internet:

  ```bash
  npx expo start --tunnel   # Expo will offer to install @expo/ngrok
  ```

> **Note:** iOS native builds (`npx expo run:ios`, simulator, App Store) require macOS — they can only run on the MacBook. The Linux server can preview via Expo Go / web, and can trigger cloud builds via EAS Build.

## Using a local backend instead of the live API

The app points at the live API by default. To test against a locally-running backend:

1. Edit `API_BASE` in [lib/api.ts](lib/api.ts).
2. On **web / Android emulator**: `http://localhost:8765/api` (or `http://10.0.2.2:8765/api` from the Android emulator).
3. On a **physical iPhone**: iOS blocks plain-HTTP by default (ATS). Use the live HTTPS API for phone testing, or add an `infoPlist.NSAppTransportSecurity` exception in [app.json](app.json) for your LAN IP.

## Shipping (App Store / TestFlight / Play Store)

No Mac required for cloud builds — [EAS Build](https://docs.expo.dev/eas/) compiles iOS on Expo's servers:

```bash
npx eas-cli login
npx eas-cli build:configure
npx eas-cli build --platform ios    # produces an IPA for TestFlight / App Store
npx eas-cli build --platform android
```

- iOS standalone builds require an **Apple Developer Program** membership (for signing).
- Android builds require a **Google Play Console** account.

## Project structure

```
mobile/
├── app/                  # expo-router file-based routes
│   ├── _layout.tsx       #   root Stack (tabs + article detail)
│   ├── (tabs)/
│   │   ├── _layout.tsx   #   tab bar: Search / Browse
│   │   ├── index.tsx     #   Search screen (GET /api/search)
│   │   ├── browse.tsx    #   Browse feed (GET /api/articles, sortable, paginated)
│   │   └── suggestions.tsx  # hidden — Suggestions (GET /api/suggestions), no tab
│   └── article/[id].tsx  # Article detail (GET /api/articles/{id})
├── components/
│   └── ArticleCard.tsx   # shared article card (score badge, title, reason)
├── lib/
│   ├── api.ts            # API base, response types, fetch helpers
│   ├── theme.ts          # shared color tokens
│   └── format.ts         # date formatting
├── app.json              # Expo app config (name, slug, scheme, icons)
├── assets/               # icons, splash
└── .vscode/              # editor config: extensions.json + settings.json
```

Search results carry a numeric `id` (same as the browse feed), and cards link
to the detail screen with `GET /api/articles/{id}`.

## VSCode tips

- Open the `mobile/` folder as its own window so the bundled settings apply.
- The recommended extensions (Expo, ESLint, Prettier, React Native Tools) are in [.vscode/extensions.json](.vscode/extensions.json) — VSCode will offer to install them.
- Formatting is applied on save via Prettier.
