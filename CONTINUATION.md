# Mobile Dev — Handoff (Linux → MacBook)

Self-contained context for continuing this work on the MacBook. Written 2026-08-19 on the Linux home server (`/home/pranav/Code/blog-feed`), where the chat history lives.

**How to use this file:** on the MacBook, either read it yourself or paste its full contents as the first message of a new Claude Code session so the assistant has the same context this chat had. Delete this file once the handoff feels done — it's a point-in-time snapshot, not a living doc.

---

## 1. What this is

**Blog Feed** — a search engine / reading list for high-signal engineering blog posts. FastAPI backend + Chroma semantic search + React web frontend. Live API: `https://blog-feed-aws.pranav-bansal.com/api` (docs at `/docs`). Web frontend (separate): `https://blog-feed.pranav-bansal.com`.

**The mobile app** (`mobile/`) is a brand-new **Expo (React Native)** client for that API. Cross-platform iOS + Android + web, **iOS-first** — the user owns an iPhone and wants native iOS eventually.

## 2. Where things stand (2026-08-19)

- Mobile app scaffolded, committed, and pushed: **`81bd269` on `dev`** (`origin/dev`). Main branch is `master` (deploy target).
- **Expo SDK 54** (`expo ~54.0.36`, RN `0.81.5`, React `19.1.0`, TS `~5.9.2`, `react-native-safe-area-context ~5.6.0`).
- The whole app is one screen: `mobile/App.tsx` — search box → `GET /api/search` → tappable article cards (opens URL in system browser). Live API default means it works with zero backend.
- Verified working: `tsc --noEmit` clean, iOS Metro bundle exports, and **the user confirmed it runs in Expo Go on their iPhone.**
- `mobile/.vscode/` (extensions + settings) is committed and un-ignored at the repo root so it travels with the repo.
- Not yet committed on the server (leave alone): `.env`, `data/*.db`, `logs/api.log`, `architecture.html`, `architecture_preview.png`.

## 3. The one rule that caused the most trouble

> **Store versions of Expo Go (App Store / Play Store) only support SDK 54.** Apple has not approved newer Expo Go builds. Any project on SDK 55+ fails to open in store Expo Go with *"Project is incompatible with this version of Expo Go."*

Implications:
- **Keep this app on SDK 54** as long as phone preview uses the store Expo Go.
- To go SDK 55+ later: use a **development build** (`npx expo run:ios` on the MacBook) — it bypasses Expo Go entirely. Don't bump the SDK without doing this.
- Source: https://docs.expo.dev/troubleshooting/expo-go-version-mismatch/ and the SDK-55 changelog.

## 4. Environment / machines

| Machine | Role |
|---|---|
| **Linux home server** (`pranav-home`, Ubuntu) | Runs the FastAPI backend + hosts this repo. Claude Code / this chat lives here. Can run `expo start` for Expo Go preview (same LAN or `--tunnel`) and trigger EAS cloud builds. **Cannot do native iOS.** |
| **MacBook** | iOS native dev: iOS Simulator, `npx expo run:ios`, App Store builds. Needs Xcode. |
| **iPhone** (user's) | Physical device for Expo Go preview. |

- Development moved to the MacBook as of 2026-08-19. **Keep both clones in sync** — commit → push → pull. Don't edit mobile files on both machines at once.
- The user develops with VSCode. On the server via Remote-SSH; now also locally on the MacBook.

## 5. MacBook setup (do once)

```bash
git clone https://github.com/artzuros/blog-feed.git
cd blog-feed && git checkout dev
cd mobile && npm install
code .          # open the mobile/ folder so .vscode/ config applies
npx expo start
#   i → iOS Simulator (needs Xcode)
#   or scan QR with iPhone Camera → Expo Go
```

Prereqs: Node ≥ 20 (`brew install node` or nvm), Xcode from the App Store (`sudo xcodebuild -license accept` after install), Expo Go already on the iPhone.

## 6. Known gotchas (hit this session)

- **`Error: ENOENT ... uv_cwd` when running npm/npx** — the shell's cwd was deleted/recreated out from under it. Fix: `cd ~/Code/blog-feed/mobile` and rerun. (Caused by scaffolding `rm -rf mobile` while a terminal sat inside it.)
- **`React Native DevTools ... chrome-sandbox ... mode 4755` (Linux only)** — non-fatal; only blocks the JS debugger. Fix if wanted: `sudo chown root:root <path>/chrome-sandbox && sudo chmod 4755 <path>`.
- **API domain** — the API is on `blog-feed-aws.pranav-bansal.com`; the *main* domain serves the web frontend and returns HTML for `/api/*` (can look like a broken API).
- **`.vscode/` is scoped to `mobile/`** — open the `mobile/` folder as its own window to get the settings and extension prompts.
- **Node on the server is v25.2.1 (nvm), conda `base` env active** — Expo SDK 54 is happy with Node ≥ 20.

## 7. Code map

```
mobile/
├── App.tsx            # the whole app: search screen + article cards
├── app.json           # Expo config: name "Blog Feed", slug, scheme, icons
├── package.json       # Expo SDK 54 deps
├── README.md          # run targets + SDK-54/Expo Go note
├── .vscode/           # extensions.json + settings.json (committed)
├── AGENTS.md          # scaffold-generated: "read Expo v54 docs before coding"
├── index.ts           # entry (registers App.tsx)
└── assets/            # icons / splash
```

Backend (repo root, for reference): `api/` (FastAPI), `core/` (fetcher, scorer, embeddings), `config/blogs.csv` (sources), `tests/` (89 tests).

## 8. Plan / next steps

Tracking lives on the server in `Code/plans/blog-feed-mobile.md` (and `Code/worklog.md`). Summary of what's next:

- [ ] **Add navigation** with `expo-router` (tabs: Search / Suggestions / Browse)
- [ ] **Browse feed screen** using `GET /api/articles` (sort by `combined_score` or recency)
- [ ] **Article detail screen** using `GET /api/articles/{id}` (+ open raw URL in browser)
- [ ] **Native iOS run on the MacBook**: `npx expo run:ios`
- [ ] **EAS Build** → TestFlight / App Store (needs Apple Developer account, $99/yr)
- [ ] **Repo hygiene** (separate, server-side): untrack `.env`, `data/*.db`, `logs/api.log`; the old API key is in git history. See `Code/plans/blog-feed-repo-hygiene.md`.

## 9. Useful links

- Expo SDK 54 docs (read before writing Expo code): https://docs.expo.dev/versions/v54.0.0/
- API docs (Swagger): https://blog-feed-aws.pranav-bansal.com/docs
- Expo Go / SDK mismatch: https://docs.expo.dev/troubleshooting/expo-go-version-mismatch/
- Backend README: [README.md](README.md) · Mobile README: [mobile/README.md](mobile/README.md)
- Repo: https://github.com/artzuros/blog-feed (dev branch has the mobile app)
