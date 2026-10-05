# Plunk

**Your camera. Your folders. Plunk.**

Take a picture. Give it a name. Pick where it goes. Plunk sends it directly from your iPhone web app to a folder on your Linux server.

**Pic → Name → Location.** Real-world context for your models.

**Ready to try it on your iPhone? → [Follow the Tailscale setup guide](docs/setup.md).**

The guide covers cloning this private repository, generating configuration, starting Docker, enabling trusted HTTPS with Tailscale Serve, installing the phone app, and verifying your first saved picture.

## What’s here

- React/TypeScript phone app at `/app`, with camera/library selection, saved servers, authentication discovery, directory browsing, progress, and upload receipts.
- Responsive launch page at `/`, setup guide at `/setup.html`, original SVG identity and generated app icons under `public/brand`.
- FastAPI Linux listener with none/bearer/Basic authentication, JPEG/PNG/HEIC decoding, orientation correction, metadata stripping, restricted roots, and persistent idempotency receipts.
- Docker Compose with Caddy HTTPS. Images travel straight to the selected listener, without a cloud relay.

## Local development

Requirements: Node 22+, pnpm, Linux Python 3.12+ (WSL works on Windows).

```sh
pnpm install
node scripts/assets.mjs
pnpm dev
```

In Linux, from the repository root:

```sh
python3 -m venv .venv
.venv/bin/pip install -r server/requirements.lock
.venv/bin/python -m scripts.dev_listener
```

Open `http://127.0.0.1:5173/app`. Add `http://127.0.0.1:8741` as a server. HTTP is allowed only for loopback development; other destinations require HTTPS. The dev listener allows only the local frontend origin and writes to `.local/uploads`. It has no authentication and binds to loopback only.

```sh
pnpm build
.venv/bin/python -m pytest server scripts -q
```

## Deploy

Use the [Tailscale setup guide](docs/setup.md) for a private installation. `python3 scripts/setup.py` creates configuration and selects `compose.tailscale.yaml`; Tailscale Serve supplies trusted HTTPS and Docker exposes only a loopback HTTP port. The listener runs as UID/GID 10001. Keep the receipt volume persistent.

The original `compose.yaml` remains available for a public domain with Caddy-managed HTTPS. For that alternative, copy `.env.example` and `server/config.example.json`, configure your hostname, origin and token, and grant UID/GID 10001 access to the configuration and destination folder. Do not mix the public and Tailscale configurations on the same installation.

For another server, deploy another listener and allow the **same installed app origin** in its configuration. Save its address in the existing phone app. Authentication belongs to each listener; no central account is involved.

The app is installable via Safari’s Add to Home Screen. V1 deliberately has no service-worker upload queue or offline guarantee. Keep the page open while uploading. Credentials are saved in localStorage; clearing site data removes them. Protect your browser profile.

## API v1

All responses are JSON; errors use `detail`. Authentication is an `Authorization: Bearer …` or `Authorization: Basic …` header, selected by listener configuration. Basic uses UTF-8 credentials. Cookies are not used.

| Endpoint | Input | Output |
| --- | --- | --- |
| `GET /api/v1/info` | Public discovery | Name, protocol version, auth mode, maximum image bytes |
| `GET /api/v1/directories` | Auth required when configured; optional `root`, `path` query | Allowed root identifiers/names, or child directory names |
| `POST /api/v1/uploads` | Multipart `image`, `name`, `root`, `path`, UUID `request_id` | Server, logical folder, filename, JPEG byte count, dimensions, request ID |

Paths are root-relative with `/` separators. Root paths never come from the client. Filenames preserve spaces and Unicode, are normalized to NFC, reject path separators/control characters/dot names, and fit within 240 UTF-8 bytes including `.jpg`. Existing files return 409; they are never overwritten. Root IDs and relative paths are distinct from display labels.

The request UUID is bound to destination, normalized filename, and input bytes. A successful retry returns the stored receipt, including after process restart. Publishing uses a same-directory hard link, so destination filesystems must support Linux hard links and directory fsync. Local ext4/XFS are appropriate; test network filesystems before use. Directory descriptors and `O_NOFOLLOW` prevent traversal through symlinks. Server administrators and processes with write access to the same directories are trusted; this is not a sandbox against a hostile co-owner of those directories.

The listener limits decoded images to 50 million pixels and uploads to 25 MB by default. Caddy caps the whole multipart request at 27 MB. Adjust both limits together for larger uploads. The journal serializes writes; this is a personal utility, not a high-throughput media service. Pending hidden files are retained to recover interrupted publication; successful uploads remove theirs. Unsent phone images remain only in the open page, not persistent storage.

JPEGs default to mode `0644`, so model tools running under another host account can read them if the parent directories allow access. Set `file_mode` to `0640` for group-only reading or `0600` for listener-owner-only reading, and arrange group/directory permissions accordingly. No executable file modes are supported.

## Brand and launch

See [the launch kit](docs/launch-kit.md), [brand notes](docs/brand.md), and [verification record](docs/verification.md). Launch screenshots come from the working app. The whiteboard demo input is an explicitly generated test fixture, not an iPhone photograph. Publishing, domain registration, physical iPhone validation, and public release are not performed by local setup.
