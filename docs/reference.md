# Listener reference


All responses are JSON; errors use `detail`. Authentication is an `Authorization: Bearer …` or `Authorization: Basic …` header, selected by listener configuration. Basic uses UTF-8 credentials. Cookies are not used.

| Endpoint | Input | Output |
| --- | --- | --- |
| `GET /api/v1/info` | Public discovery | Name, protocol version, auth mode, maximum image bytes |
| `POST /api/v1/pair` | Public; JSON `{"code"}` from `plunk pair` | Name and bearer token. Single use, 10-minute expiry, 5 attempts |
| `GET /api/v1/directories` | Auth required when configured; optional `root`, `path` query | Allowed root identifiers/names, or child directory names |
| `POST /api/v1/uploads` | Multipart `image`, `name`, `root`, `path`, UUID `request_id` | Server, logical folder, filename, JPEG byte count, dimensions, request ID |

Paths are root-relative with `/` separators. Root paths never come from the client. Filenames preserve spaces and Unicode, are normalized to NFC, reject path separators/control characters/dot names, and fit within 240 UTF-8 bytes including `.jpg`. Existing files return 409; they are never overwritten. Root IDs and relative paths are distinct from display labels.

The request UUID is bound to destination, normalized filename, and input bytes. A successful retry returns the stored receipt, including after process restart. Publishing uses a same-directory hard link, so destination filesystems must support Linux hard links and directory fsync. Local ext4/XFS are appropriate; test network filesystems before use. Directory descriptors and `O_NOFOLLOW` prevent traversal through symlinks. Server administrators and processes with write access to the same directories are trusted; this is not a sandbox against a hostile co-owner of those directories.

The listener limits decoded images to 50 million pixels and uploads to 25 MB by default. Caddy caps the whole multipart request at 27 MB. Adjust both limits together for larger uploads. The journal serializes writes; this is a personal utility, not a high-throughput media service. Pending hidden files are retained to recover interrupted publication; successful uploads remove theirs. Unsent phone images remain only in the open page, not persistent storage.

JPEGs default to mode `0644`, so model tools running under another host account can read them if the parent directories allow access. Set `file_mode` to `0640` for group-only reading or `0600` for listener-owner-only reading, and arrange group/directory permissions accordingly. No executable file modes are supported.

