# A little setup. A lot less sending things to yourself.

Set up Plunk once on your Linux server, connect your iPhone, and give your pictures a home. This guide uses **Tailscale and the native installer**. For containers, follow the [Docker guide](docker.md).

## 1. Check the basics

Use a Linux server with a **systemd user session**, **Python 3.12 or newer with venv**, **Node 22 or newer with Corepack**, and **Git**. Run the installer as your normal user, not root. The listener will have that user’s access to your destination folders.

```bash
python3 --version
node --version
corepack --version
git --version
systemctl --user status
tailscale status
```

On Ubuntu 24.04, the Python/Git prerequisites are:

```bash
sudo apt-get update
sudo apt-get install -y git python3 python3-venv
```

Install Node using the [official Node instructions](https://nodejs.org/en/download). If your Node installation does not include Corepack, install it with `npm install --global corepack` using the permissions appropriate to your Node installation. Plunk uses `corepack pnpm` directly; you do not need a separate global pnpm installation.

Connect Tailscale on both server and iPhone. The phone must be allowed to reach the server by your tailnet access rules. Enable MagicDNS and HTTPS certificates in your Tailscale administration settings. [Tailscale Serve](https://tailscale.com/docs/features/tailscale-serve) supplies trusted HTTPS inside your tailnet.

Allow your Linux user to manage Serve, and keep its service running after logout:

```bash
sudo tailscale set --operator="$USER"
sudo loginctl enable-linger "$USER"
```

These are one-time administration steps. The installer itself runs without `sudo`.

## 2. Install Plunk

The repository is currently private. If cloning says “repository not found,” authenticate a GitHub account that has access. With the [GitHub CLI](https://cli.github.com/) installed:

```bash
gh auth login --hostname github.com --git-protocol https --web
gh auth setup-git
```

Clone into a directory you will keep, then install:

```bash
git clone https://github.com/bx0-val/plunk.git
cd plunk
./scripts/plunk.py install
```

The installer creates a Python environment, builds the phone app, generates a bearer token, starts a systemd user service, and points Tailscale Serve at it. It selects free HTTPS and loopback ports; existing Serve apps keep their own ports. The default first destination is `~/Plunk`.

If Serve asks you to enable HTTPS, open the link it prints, enable the feature, and rerun the installer. Use the **exact address it prints**, including any port such as `:8443`. [Serve command reference](https://tailscale.com/docs/reference/tailscale-cli/serve)

The `plunk` command is linked in `~/.local/bin`. If your shell cannot find it:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Add that line to your shell’s startup file to keep it for future sessions. You can also run `~/.local/bin/plunk` directly.

## 3. Pair your iPhone

The installer finishes with a pairing card. Show a fresh one anytime:

```bash
plunk pair
```

1. Keep **Tailscale connected** on the iPhone. Scan the QR code with its Camera app, or open the printed link in Safari.
2. In Safari, choose **Share → Add to Home Screen**. Name it **Plunk**.
3. Open **Plunk from that new icon** so the connection is saved in the installed app’s storage.
4. Tap **Connect a server**, or the gear → **Pair with a code**. Enter the six digits from the terminal and tap **Connect this server**.
5. When it says **You’re connected**, tap **Let’s Plunk**.

A code works once, expires after ten minutes, and is disabled after five wrong attempts. Running `plunk pair` replaces the previous code. If the Home Screen app receives a valid pairing link directly, it connects automatically. Safari waits for your tap so it does not consume the code before installation.

Pairing connects to the server **hosting the app you have open**. Use **Use an address** for other servers; see below. The QR contains only the expiring code, never the permanent token. Narrow terminals show a copyable link when the QR will not fit.

## 4. Give your pictures a home

On the server, go to a project you want to send pictures to:

```bash
cd ~/projects/robot
plunk here --name Robot
```

That folder is now a destination. No service restart. Or add another existing folder by path:

```bash
plunk add ~/notes --name Notes
plunk ls
```

Both destinations appear as tiles in the phone’s folder grid. You can open their subfolders. One saved server skips the server picker; with several, choose a server first. Plunk remembers the last successfully used folder on each server.

To remove a destination, use its ID from `plunk ls`:

```bash
plunk rm robot
```

Its files stay on disk. Add another destination before removing your last one. Run `plunk here --name NewName` in an existing destination to rename its tile without changing its ID.

## 5. Your first Plunk

1. **Take a pic**, or choose one from Photos.
2. Preview it and tap **Name it**. Enter `first-plunk`.
3. Tap **Choose a location**, open **Robot**, then tap **Plunk here**.
4. Keep Plunk open until the **Plunked.** receipt confirms the server, folder, and filename.

On your server:

```bash
ls -lh ~/projects/robot/first-plunk.jpg
```

You have an upright JPEG, ready for tools with access to that folder. Plunk does not automatically attach it to model conversations. Existing filenames are never overwritten; choose another name if one is already taken.

## Updates and everyday commands

From the repository directory:

```bash
git pull --ff-only
plunk install --rebuild
```

You keep your configuration, token, destinations, and uploaded pictures. An update prints a fresh pairing code, but already connected phones do not need to pair again. Close and reopen the phone app to load the new interface.

```bash
plunk status       # Service health, app address, destination count
plunk ls           # Destinations and IDs
plunk pair         # Connect another phone
plunk url          # Just the app URL, useful in scripts
plunk logs         # Recent service logs
plunk --help       # All commands
```

Color follows the terminal automatically. Use `plunk pair --color always` to force it, `--color never` for plain output, or set `NO_COLOR`. QR codes are rendered only when the terminal is wide enough.

Native files: configuration at `~/.config/plunk/config.json`, receipts and pairing state at `~/.local/state/plunk`, service at `~/.config/systemd/user/plunk.service`. Keep the repository in place: the service runs its `.venv` and built app. Back up the configuration, receipt state, and your picture folders. The configuration contains a permanent credential; keep it private.

## Add another server to the same phone app

Install Plunk on the second server. In its `~/.config/plunk/config.json`, add the **first app’s exact origin**, including the port, to `origins`. Keep the second server’s own origin too:

```json
"origins": [
  "https://second.tail1234.ts.net:8443",
  "https://first.tail1234.ts.net"
]
```

Restart the second listener after changing authentication or origins:

```bash
systemctl --user restart plunk
```

In the existing phone app, choose gear → **Use an address**. Enter the second server’s HTTPS base address without `/app`, tap **Connect to server**, and supply the requested credentials. For a native installation, copy `auth.token` from its private config into the **Secret token** field, then **Test & save server**. Token, Basic, or no-auth requirements are discovered from that listener.

The installed app’s pairing code field always pairs with its own origin. It cannot redeem another server’s code. Once saved by address, either server is available without switching apps.

## If something gets in the way

| What you see | Next step |
| --- | --- |
| `plunk: command not found` | Add `~/.local/bin` to PATH as shown above, or use the full path. |
| Python environment fails | Check Python 3.12+ and the venv package. Read the printed package-install error. |
| Build needs Corepack | Check `node --version` and `corepack --version`. Install the missing prerequisite and rerun. |
| Cannot connect to the user service manager | Run from a normal user login/SSH session on a systemd host, not through `sudo`. |
| Service stops after logging out | Run `sudo loginctl enable-linger "$USER"`. |
| Tailscale Serve permission denied | Run `sudo tailscale set --operator="$USER"`, then rerun the installer. |
| HTTPS port is in use | Check `tailscale serve status`. Choose an unused port with `plunk install --https-port 8443`. Do not reset another app’s Serve configuration. |
| Phone cannot open the site | Connect Tailscale; check access rules and the full printed `.ts.net` hostname/port. |
| Code is expired or already used | Run `plunk pair` again and enter the new code in the app opened from its icon. |
| Site opens but directories fail | Check the listener’s credentials, allowed `origins`, and destination permissions. |
| Folder cannot be written | The service runs as the installing user. That user needs access to the destination. |
| Picture fails to send | Keep the page open and retry. If the name exists, choose a new one. |
| Preview is unavailable | Try **Choose from photos**. Report the iOS version and format if it persists. |

Unsent pictures live only in the open page. Switching apps may interrupt an upload; reloading discards the current picture. V1 has no background queue. See the [verification record](verification.md) for checks performed and physical-device checks still needed.
