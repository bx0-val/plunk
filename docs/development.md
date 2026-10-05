# Build and contribute

Requirements: Node 22+, pnpm (version pinned in `package.json`), Linux Python 3.12+. WSL works on Windows; the listener uses Linux directory descriptors and hard links.

```bash
pnpm install
pnpm assets
pnpm dev
```

In a Linux terminal at the repository root:

```bash
python3 -m venv .venv
.venv/bin/pip install -r server/requirements.lock
.venv/bin/python -m scripts.dev_listener
```

Open `http://127.0.0.1:5173/app`. In settings, choose **Use an address** and connect to `http://127.0.0.1:8741`. HTTP is allowed for loopback development only. This test listener has no authentication, binds to loopback, accepts only the configured local frontend origins, and saves to `.local/uploads`.

## Verify a change

```bash
pnpm build
pnpm exec playwright install chromium
pnpm test:ui
.venv/bin/python -m pytest server scripts -q
```

The browser suite uses stubbed listener responses to exercise focus, folder navigation, first-server setup, pairing, retry IDs, small screens, and reduced motion. It does not prove camera access or the iOS keyboard. Listener tests cover actual image conversion and file operations. CI additionally builds Docker images and performs real uploads through the container proxy.

Use a real Linux listener to check the complete picture → name → folder → receipt path. For UI changes, inspect the app at 320px and 390px widths and desktop size. Check foreground errors, long folder names, and touch targets. Report physical iPhone/Safari/Home Screen and remote-server checks separately from browser emulation.

## Where things live

| Path | Purpose |
| --- | --- |
| `src/phone.tsx`, `src/api.ts` | Phone workflow and listener requests |
| `src/style.css`, `src/experience.css` | Layout and shared dark theme |
| `src/landing.tsx` | Product page |
| `scripts/plunk.py`, `scripts/plunk_ui.py` | Native installation, destinations, pairing, terminal presentation |
| `server/app.py` | Listener API, conversion, guarded file writes, receipt journal |
| `docs/` | Source guides, reference, brand and verification notes |
| `scripts/build-guide.mjs` | Generates hosted HTML guides during `pnpm build` |
| `scripts/assets.mjs` | App icons, labeled whiteboard fixture, social graphic |

Launch screenshots must show the actual app. Label fixtures honestly and record the environment. Regenerate social artwork after replacing `public/launch/app-success.png`.

Pull requests should describe the user-visible result, relevant validation, and any checks that could not be performed. Never attach real tokens, pairing links, configuration, or personal photos to issues, screenshots, or logs.
