# Docker installation with Tailscale

**The result:** an HTTPS address such as `https://my-server.tail1234.ts.net/app`, accessible from your iPhone whenever Tailscale is connected. Pictures go into `/srv/plunk/pictures` on the server.

Use **Tailscale Serve**, which keeps the app private to your tailnet. No router port forwarding, purchased domain, or manually installed iPhone certificate is needed. [Tailscale Serve documentation](https://tailscale.com/docs/features/tailscale-serve)

Prefer a native install? Follow the [main setup guide](setup.md).

## 1. Check your server and phone

On the **Linux server**, open a terminal or SSH session. These instructions assume a normal Linux host with Docker Engine (not rootless Docker), Docker Compose v2, Git, and Python 3. On Ubuntu/Debian, install the small tools with:

```bash
sudo apt-get update
sudo apt-get install -y git python3 curl gh
```

Check Docker and Tailscale:

```bash
sudo docker version
sudo docker compose version
tailscale status
```

Docker should show both Client and Server. If Docker is missing, install Docker Engine and its Compose plugin using the official instructions for [Ubuntu](https://docs.docker.com/engine/install/ubuntu/) or [Debian](https://docs.docker.com/engine/install/debian/), then return here. Other distributions can use the [Docker installation index](https://docs.docker.com/engine/install/).

On the **iPhone**, connect Tailscale to the same tailnet. Your tailnet access rules must allow the phone to reach this server.

Check whether this server already uses Serve:

```bash
sudo tailscale serve status
```

If another app already uses HTTPS port **443**, use **8443** for Plunk when asked in step 3. Do not reset an existing Serve configuration. The resulting Plunk URL will include `:8443`.

## 2. Get Plunk from GitHub

The repository is private. Sign in as `bx0-val` (or another GitHub account granted access) on the server. This opens a device-code login you can complete from another computer; your GitHub password is not used as a Git password.

```bash
gh auth login --hostname github.com --git-protocol https --web
gh auth setup-git
git clone https://github.com/bx0-val/plunk.git
cd plunk
```

If the server is already authenticated with repository access, just run the clone and `cd` commands. Keep this repository directory: you will use it for updates and server logs.

## 3. Configure it once

```bash
python3 scripts/setup.py
```

The helper asks for:

| Prompt | What to enter |
| --- | --- |
| Tailscale DNS name | Press Enter if the detected name is correct; otherwise enter the full `my-server.tail1234.ts.net` name. No `https://` or path. |
| HTTPS port | Press Enter for `443`; use `8443` if Serve already hosts another app on 443. |
| Server name | A friendly name, such as `Home lab`. |
| New picture folder | Press Enter for `/srv/plunk/pictures`. Start with this new folder for the first test. |

It creates `.env` and `config.json`, generates a secret token, and prints the exact remaining commands for your choices. Existing configuration is never overwritten. You do not need Node or Python packages on the host; Docker builds the application.

## 4. Start Plunk

Run the commands the helper prints. With the default picture folder, the Docker portion is:

```bash
sudo chgrp 10001 config.json
chmod 640 config.json
sudo install -d -o 10001 -g 10001 -m 755 /srv/plunk/pictures
sudo docker compose up -d --build
```

The first build downloads dependencies and can take several minutes. The configuration gives the container access to the new picture folder; it does not expose the server's entire filesystem. If you selected a different folder, use the helper's printed directory command instead.

Check it:

```bash
sudo docker compose ps
curl --fail http://127.0.0.1:8787/api/v1/info
```

Both containers should be running. The `curl` command should return JSON containing your server name and `"auth":"bearer"`. Plunk's HTTP port is bound to **127.0.0.1 only**. The listener has no host port exposed.

## 5. Give it Tailscale HTTPS

For the default port:

```bash
sudo tailscale serve --bg --https=443 http://127.0.0.1:8787
sudo tailscale serve status
```

If you chose 8443, use this command instead of the first one:

```bash
sudo tailscale serve --bg --https=8443 http://127.0.0.1:8787
```

If Tailscale prints a link asking you to enable Serve/HTTPS certificates, open it, enable the feature for your tailnet, then rerun the command. Serve manages the HTTPS certificate. The `--bg` setting persists across reboots. [Serve command reference](https://tailscale.com/docs/reference/tailscale-cli/serve)

Copy the **exact HTTPS URL** printed by Serve, including `:8443` if present. Use the full `.ts.net` hostname, not a short hostname or a `100.x.x.x` address.

## 6. Install it on your iPhone

1. Confirm the **Tailscale app is connected**.
2. Open **Safari** and visit the HTTPS URL followed by `/app`.
3. Use Safari's **Share → Add to Home Screen**. Name it **Plunk** and add it.
4. Open **Plunk from its new Home Screen icon**. Configure servers here so credentials are saved in the installed app's storage.
5. Tap the **gear** in the top-right corner.
6. Tap **Use an address**. Enter a friendly server name and the **base HTTPS URL**, without `/app`.
7. Tap **Connect to server**. A secret-token field appears.

Back in the server terminal, display your token:

```bash
python3 scripts/setup.py --show-token
```

Copy that value into the phone's **Secret token** field and tap **Test & save server**. You should see a connected-and-saved message. Close settings.

## 7. Your first Plunk

1. Tap **Take a pic**. Allow camera access if asked and take a picture.
2. Preview it, tap **Name it**, and enter **first-plunk**.
3. Tap **Choose a location**, open **Pictures** (a single saved server is selected automatically).
4. Tap **Plunk here**. Keep the app open until it says **Plunked.**

On the server:

```bash
ls -lh /srv/plunk/pictures/first-plunk.jpg
```

That is the actual JPEG. A model tool with access to that directory can now read it. Plunk does not automatically attach it to a model conversation.

To test folder browsing, make a folder and take another picture:

```bash
sudo install -d -o 10001 -g 10001 -m 755 /srv/plunk/pictures/project-context
```

Choose **Pictures → project-context** on the phone. Plunk remembers the last folder for that server. Filenames never overwrite existing pictures; an existing name sends you back to naming.

## Add a second server

Repeat steps 1–5 on the second Linux server. Before starting its listener, edit its `config.json` so `origins` includes the HTTPS address of the **first app installed on your phone**, as well as its own address:

```json
"origins": [
  "https://first-server.tail1234.ts.net",
  "https://second-server.tail1234.ts.net"
]
```

Include the port for any URL using 8443. Restart with `sudo docker compose restart listener` after editing. In the existing phone app, add the second server's HTTPS address and its own token. You keep one app, pick either server, and browse that server's allowed folders.

## Updates and useful commands

Run these from the cloned `plunk` directory:

```bash
# Update code and rebuild. Your configuration, pictures, and receipt volume remain.
git pull --ff-only
sudo docker compose up -d --build

# View recent logs.
sudo docker compose logs --tail=100 listener web

# Stop Plunk, retaining data.
sudo docker compose down

# Start again.
sudo docker compose up -d
```

Do not add `-v` to `docker compose down`: the receipt volume helps safely recover uploads after lost responses. Back up your picture directory, `config.json`, `.env`, and persistent Docker volumes. The generated configuration and local pictures are ignored by Git.

## If something doesn't work

| What you see | What to check |
| --- | --- |
| GitHub says “repository not found” | Run `gh auth status`. The account must have access to the private `bx0-val/plunk` repository. |
| `docker compose` is unavailable | Install the Compose v2 plugin from Docker's instructions above. |
| Build or startup fails | Run `sudo docker compose logs --tail=100 listener web`. Check available disk/memory and the first build error. |
| Listener cannot read `config.json` | Run `sudo chgrp 10001 config.json` and `chmod 640 config.json` again. |
| The loopback `curl` fails | Containers must be running; check `sudo docker compose ps` and logs. |
| Safari cannot open the address | Connect Tailscale on both devices; check Serve status, tailnet access rules, and the full HTTPS `.ts.net` URL/port. |
| Safari shows a certificate warning | Use the full hostname printed by Serve. Confirm HTTPS is enabled; do not work around this with plain HTTP. |
| The app cannot connect but Safari opens the site | The URL in `config.json` → `origins` must exactly match the app's origin, including port. Restart the listener after editing it. |
| Credentials fail | Show the token again and copy it without spaces. Each server has its own token. |
| The folder is not writable | For the new dedicated folder, UID 10001 needs write access. Do not recursively change ownership of an existing project. |
| Camera preview fails | Try **Choose from photos**. Capture the error and iOS version; physical-device testing is the next validation step. |
| Camera upload vanishes when switching apps | Keep Plunk in the foreground. V1 has no background queue; reloading discards unsent pictures. |

For existing project folders, grant the listener's UID 10001 appropriate directory access using your server's normal group/ACL policy. Start with the dedicated test folder first. JPEGs are mode `0644` by default so other host accounts can read them when directory permissions allow.

**Verification:** See the [verification record](verification.md) for automated checks and remaining device checks.
