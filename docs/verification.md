# Verification — October 5, 2026

## Experience polish

- `pnpm build` passes the TypeScript check, hosted-guide generation, and optimized Vite build.
- **53 Linux tests** pass on Ubuntu/WSL. Existing listener coverage includes none/bearer/Basic auth, invalid credentials, CORS, JPEG/PNG/HEIF, orientation, EXIF removal, dimensions, permissions, filename validation, traversal/symlink boundaries, duplicate names, persistent/concurrent retries, interrupted publication and multipart bodies, size limits, disk-full errors, and denied writes. New CLI tests cover pairing state, interrupted code replacement, display-name ambiguity, destination renaming, port/address changes, color settings, control-character filtering, and plain/copyable URLs.
- **7 Chromium tests** at phone size cover synchronous filename focus, the two-column folder grid, skipping a single server, multiple-server choice, remembered folders, first-server setup with the current picture retained, lost-response retry IDs, one-time pairing across settings remounts, explicit browser pairing, 320px layout, dark default, and reduced motion. Listener responses in this suite are stubbed; it is not a physical iOS test.
- Separately, the real production app redeemed a code from a **bearer-authenticated Linux listener**, saved the server, selected the whiteboard fixture, named it `the-plan`, navigated Projects / Whiteboards, and received a save receipt. The actual file is `.local/experience-demo/projects/Whiteboards/the-plan.jpg`: 1200 × 900, RGB JPEG, no EXIF.
- A second real flow reused the remembered folder. An existing name returned to the naming screen with the picture retained; choosing the suggested `the-plan-2.jpg` then saved successfully.
- Refreshed app screenshots and the **18.45-second, 390 × 844, 20 fps H.264 recording** show real UI and Linux responses. The input is a generated whiteboard fixture, not an iPhone camera photograph. The social card includes the actual receipt screenshot.
- Visual checks covered 390px phone and 1440px desktop layouts; automated overflow checks cover 320px. The photo preview fits the whole picture without cropping. Terminal pairing was exercised in a real TTY with the installed QR dependency; permanent tokens are not printed.
- Automated axe checks reported zero violations on the capture, naming, error, success, pairing, landing, and setup screens. Dark gradients and rotated illustration text leave contrast items for manual review. Main palette pairs were checked separately; this is not a complete assistive-technology audit.
- All 58 local documentation/hosted-guide references checked resolve. Guides are generated from Markdown; the native Tailscale path is primary, with Docker and API reference separated.

## Continuous verification

GitHub Actions builds the frontend, runs browser and Linux tests, builds both Docker images, then performs actual authenticated JPEG uploads, safe retry checks, and a 25 MiB request through the Tailscale container proxy. See [the workflow runs](https://github.com/bx0-val/plunk/actions/workflows/ci.yml) for the status of a particular commit.

The [initial successful container run](https://github.com/bx0-val/plunk/actions/runs/37269583880) established the Docker path before this visual pass. It does not verify a live Tailscale connection or an iPhone. Local Docker Desktop is not running, so container checks run in CI.

## Still needs a real device or deployment

- iPhone camera and HEIC samples, Safari and Home Screen installation/storage, native keyboard appearance after **Name it**, and foreground/background transitions. Synchronous focus is tested in Chromium; only an iPhone can confirm its keyboard behavior.
- The actual Tailscale tailnet, HTTPS certificate issuance, remote connectivity, and systemd installation on the target host. No user's server was changed during this pass.
- A distinguishable public identity and name/trademark clearance; see the [launch kit](launch-kit.md). No domain was purchased and no public release was made.

## Reproduce

Follow [development](development.md). Run `pnpm build`, `pnpm test:ui`, and `.venv/bin/python -m pytest server scripts -q`. Start the local frontend and Linux test listener for a real upload; `pnpm assets` generates the labeled fixture.

The Python test dependency emits a Starlette deprecation warning about its httpx TestClient adapter. Tests pass; this is a dependency maintenance item, not a verified production failure.
