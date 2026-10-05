import { useEffect, useRef, useState, type FormEvent } from "react";
import { flushSync } from "react-dom";
import {
  ArrowLeft,
  ArrowRight,
  Camera,
  Check,
  ChevronRight,
  Folder,
  ImagePlus,
  Plus,
  Server as ServerIcon,
  Settings,
  X,
} from "lucide-react";
import {
  type Info,
  type Location,
  type Receipt,
  type Server,
  UploadError,
  isStandalone,
  jpegName,
  loadServers,
  normalizeUrl,
  pair,
  readPairCode,
  request,
  saveServers,
  upload,
  validateName,
} from "./api";
import { Wordmark } from "./shared";

const emptyServer = (): Server => ({
  id: crypto.randomUUID(),
  name: "",
  url: "",
  auth: "none",
  token: "",
  username: "",
  password: "",
});

function ServerSettings({
  servers,
  onSave,
  onClose,
  pairCode = "",
  onPaired,
}: {
  servers: Server[];
  onSave: (value: Server[]) => void;
  onClose: () => void;
  pairCode?: string;
  onPaired: () => void;
}) {
  const [draft, setDraft] = useState<Server>(emptyServer);
  const [detected, setDetected] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [code, setCode] = useState(pairCode);
  const [pairError, setPairError] = useState("");
  const [pairNotice, setPairNotice] = useState("");
  const [mode, setMode] = useState<"pair" | "address">("pair");
  const autoPaired = useRef(false);
  const standalone = isStandalone();
  async function pairHere(event?: FormEvent) {
    event?.preventDefault();
    const digits = code.replace(/\D/g, "");
    if (digits.length !== 6) {
      setPairError(
        "Enter the 6-digit code that plunk pair shows on the server.",
      );
      return;
    }
    setBusy(true);
    setPairError("");
    setPairNotice("");
    try {
      // The app is served by the listener it pairs with, so its own origin is the server address.
      const base = window.location.origin;
      const result = await pair(base, digits);
      const existing = servers.find((s) => s.url === base);
      const server: Server = {
        ...(existing ?? emptyServer()),
        name: existing?.name || result.name,
        url: base,
        auth: "bearer",
        token: result.token,
        username: "",
        password: "",
      };
      // Save the credential immediately: the code has already been consumed.
      onSave([...servers.filter((s) => s.id !== server.id), server]);
      onPaired();
      setCode("");
      setPairNotice(`${server.name} is ready for your pictures.`);
    } catch (e) {
      setPairError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  useEffect(() => {
    // From the QR link inside the Home Screen app, pair without another tap.
    if (pairCode && standalone && !autoPaired.current) {
      autoPaired.current = true;
      void pairHere();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const update = (patch: Partial<Server>) => {
    setDraft((s) => ({ ...s, ...patch }));
    setNotice("");
  };
  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const normalized = { ...draft, url: normalizeUrl(draft.url) };
      const info = await request<Info>(normalized, "info", true);
      if (
        info.version !== 1 ||
        !["none", "bearer", "basic"].includes(info.auth)
      )
        throw new Error("This listener uses an unsupported protocol.");
      const next = {
        ...normalized,
        name: draft.name.trim() || info.name,
        auth: info.auth,
        // Pasted secrets often carry invisible whitespace; the field is masked, so trim it.
        token: draft.token.trim(),
        username: draft.username.trim(),
      };
      setDraft(next);
      setDetected(true);
      if (
        (info.auth === "bearer" && !next.token) ||
        (info.auth === "basic" && (!next.username || !next.password))
      ) {
        setNotice(
          "Connected. Add the credentials this server requires, then test and save.",
        );
        return;
      }
      await request(next, "directories");
      const clean = {
        ...next,
        token: next.auth === "bearer" ? next.token : "",
        username: next.auth === "basic" ? next.username : "",
        password: next.auth === "basic" ? next.password : "",
      };
      onSave([...servers.filter((s) => s.id !== clean.id), clean]);
      setDraft(emptyServer());
      setDetected(false);
      setNotice(`${clean.name} is connected and saved.`);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="settings-panel" aria-labelledby="settings-title">
      <div className="section-top">
        <span className="eyebrow">ONE-TIME SETUP</span>
        <button
          className="icon-button"
          onClick={onClose}
          disabled={busy}
          aria-label="Close settings"
        >
          <X />
        </button>
      </div>
      <h1 id="settings-title">
        {servers.length ? "Your servers" : "Connect a server"}
        <span className="orange">.</span>
      </h1>
      <p className="muted">A few details now. Just a tap next time.</p>
      <div className="saved-servers">
        {servers.map((s) => (
          <div className="saved-row" key={s.id}>
            <ServerIcon size={20} />
            <div>
              <strong>{s.name}</strong>
              <small>{s.url}</small>
            </div>
            <button
              disabled={busy}
              className="text-button"
              onClick={() => {
                setDraft(s);
                setMode("address");
                setDetected(true);
                setError("");
                setNotice("");
              }}
            >
              Edit
            </button>
            <button
              disabled={busy}
              className="icon-button"
              aria-label={`Remove ${s.name}`}
              onClick={() => {
                onSave(servers.filter((x) => x.id !== s.id));
                if (draft.id === s.id) {
                  setDraft(emptyServer());
                  setDetected(false);
                }
              }}
            >
              <X size={18} />
            </button>
          </div>
        ))}
      </div>
      <div
        className="connection-tabs"
        role="group"
        aria-label="Connection method"
      >
        <button
          type="button"
          aria-pressed={mode === "pair"}
          disabled={busy}
          onClick={() => setMode("pair")}
        >
          Pair with a code
        </button>
        <button
          type="button"
          aria-pressed={mode === "address"}
          disabled={busy}
          onClick={() => setMode("address")}
        >
          Use an address
        </button>
      </div>
      {mode === "pair" &&
        (pairNotice ? (
          <div className="paired-card" role="status">
            <span className="paired-check">
              <Check size={28} />
            </span>
            <h2>You’re connected.</h2>
            <p className="muted">{pairNotice}</p>
            <button className="button primary wide" onClick={onClose}>
              Let’s Plunk <ArrowRight size={18} />
            </button>
          </div>
        ) : (
          <form className="pair-form" onSubmit={pairHere}>
            <fieldset disabled={busy}>
              <legend>Six digits. You’re in.</legend>
              <p className="pair-host">
                <ServerIcon size={16} />
                {window.location.host}
              </p>
              {pairCode && !standalone && (
                <p className="notice">
                  For the best experience, add Plunk to your Home Screen first
                  (Share → Add to Home Screen), open it from the icon, and enter
                  this code there. Or pair this browser now.
                </p>
              )}
              <label>
                Run <code>plunk pair</code> on the server and enter its code
                <input
                  className="pair-code"
                  aria-label="Pairing code"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  placeholder="123 456"
                  maxLength={7}
                  value={code}
                  onChange={(e) => {
                    setCode(e.target.value);
                    setPairError("");
                  }}
                />
              </label>
              {pairError && (
                <p className="error" role="alert">
                  {pairError}
                </p>
              )}
              {pairNotice && (
                <p className="notice" role="status">
                  {pairNotice}
                </p>
              )}
              <button className="button primary wide" type="submit">
                {busy ? "Connecting…" : "Connect this server"}
                <ArrowRight size={18} />
              </button>
            </fieldset>
          </form>
        ))}
      {mode === "address" && (
        <form onSubmit={submit}>
          <fieldset disabled={busy}>
            <legend>
              {servers.some((s) => s.id === draft.id)
                ? "Edit server"
                : "Add a server"}
            </legend>
            <label>
              Server name <span className="optional">optional</span>
              <input
                value={draft.name}
                onChange={(e) => update({ name: e.target.value })}
                placeholder="Home lab"
                autoComplete="off"
                maxLength={80}
              />
            </label>
            <label>
              HTTPS address
              <input
                type="url"
                required
                value={draft.url}
                onChange={(e) => {
                  update({
                    url: e.target.value,
                    token: "",
                    username: "",
                    password: "",
                  });
                  setDetected(false);
                }}
                placeholder="https://photos.example.com"
                autoCapitalize="none"
                autoCorrect="off"
              />
            </label>
            {detected && (
              <div className="auth-note">
                Authentication:{" "}
                <strong>
                  {draft.auth === "none"
                    ? "None"
                    : draft.auth === "bearer"
                      ? "Secret token"
                      : "Username & password"}
                </strong>
              </div>
            )}
            {detected && draft.auth === "bearer" && (
              <label>
                Secret token
                <input
                  type="password"
                  required
                  value={draft.token}
                  onChange={(e) => update({ token: e.target.value })}
                  autoComplete="off"
                />
              </label>
            )}
            {detected && draft.auth === "basic" && (
              <>
                <label>
                  Username
                  <input
                    required
                    value={draft.username}
                    onChange={(e) => update({ username: e.target.value })}
                    autoCapitalize="none"
                    autoComplete="username"
                  />
                </label>
                <label>
                  Password
                  <input
                    type="password"
                    required
                    value={draft.password}
                    onChange={(e) => update({ password: e.target.value })}
                    autoComplete="current-password"
                  />
                </label>
              </>
            )}
            <p className="fine-print">
              Credentials stay in this browser’s storage. Anyone using this
              browser profile can access them. Removing a server clears its
              saved credentials.
            </p>
            {error && (
              <p className="error" role="alert">
                {error}
              </p>
            )}
            {notice && (
              <p className="notice" role="status">
                {notice}
              </p>
            )}
            <button className="button primary wide" type="submit">
              {busy
                ? "Checking connection…"
                : detected
                  ? "Test & save server"
                  : "Connect to server"}
              <ArrowRight size={18} />
            </button>
          </fieldset>
        </form>
      )}
      <a
        className="setup-help"
        href="/setup.html"
        target="_blank"
        rel="noreferrer"
      >
        Need a listener? Setup instructions ↗
      </a>
    </section>
  );
}

export function PhoneApp() {
  const [servers, setServers] = useState(loadServers);
  const [pairCode, setPairCode] = useState(readPairCode);
  const [settings, setSettings] = useState(() => Boolean(pairCode));
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState("");
  const [previewFailed, setPreviewFailed] = useState(false);
  const [name, setName] = useState("");
  const [selected, setSelected] = useState<Server | null>(null);
  const [location, setLocation] = useState<Location | null>(null);
  const [roots, setRoots] = useState<{ id: string; name: string }[]>([]);
  const [folders, setFolders] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState("");
  const [receipt, setReceipt] = useState<Receipt | null>(null);
  const [conflict, setConflict] = useState(false);
  const camera = useRef<HTMLInputElement>(null);
  const library = useRef<HTMLInputElement>(null);
  const requestRef = useRef<{ key: string; id: string } | null>(null);
  const browseVersion = useRef(0);
  const heading = useRef<HTMLHeadingElement>(null);
  const nameInput = useRef<HTMLInputElement>(null);
  useEffect(() => {
    if (!file) {
      setPreview("");
      return;
    }
    const url = URL.createObjectURL(file);
    setPreview(url);
    setPreviewFailed(false);
    return () => URL.revokeObjectURL(url);
  }, [file]);
  useEffect(() => {
    if (step === 2 && !receipt) {
      if (document.activeElement !== nameInput.current)
        nameInput.current?.focus({ preventScroll: true });
    } else heading.current?.focus();
  }, [step, receipt]);
  useEffect(() => {
    // Keep the one-time code out of history and any Home Screen bookmark.
    if (pairCode) history.replaceState(null, "", window.location.pathname);
  }, [pairCode]);
  useEffect(() => {
    if (!file || receipt) return;
    const prevent = (e: BeforeUnloadEvent) => {
      e.preventDefault();
    };
    window.addEventListener("beforeunload", prevent);
    return () => window.removeEventListener("beforeunload", prevent);
  }, [file, receipt]);
  function persist(value: Server[]) {
    saveServers(value);
    setServers(value);
  }
  function openName() {
    // iOS only opens its keyboard while focus is inside the original tap gesture.
    flushSync(() => setStep(2));
    nameInput.current?.focus({ preventScroll: true });
  }
  function openLocation() {
    setStep(3);
    if (servers.length === 1 && selected?.id !== servers[0].id)
      void browse(servers[0], servers[0].last || null);
  }
  function chooseFile(value?: File) {
    if (!value) return;
    setFile(value);
    setError("");
    setReceipt(null);
    requestRef.current = null;
  }
  async function browse(server: Server, next: Location | null) {
    const version = ++browseVersion.current;
    setSelected(server);
    setLocation(null);
    setFolders([]);
    setRoots([]);
    setBusy(true);
    setError("");
    try {
      if (next) {
        const result = await request<{ directories: string[] }>(
          server,
          `directories?root=${encodeURIComponent(next.root)}&path=${encodeURIComponent(next.path)}`,
        );
        if (version !== browseVersion.current) return;
        setFolders(result.directories);
        setLocation(next);
      } else {
        const result = await request<{ roots: { id: string; name: string }[] }>(
          server,
          "directories",
        );
        if (version !== browseVersion.current) return;
        setRoots(result.roots);
      }
    } catch (e) {
      if (version === browseVersion.current) setError((e as Error).message);
    } finally {
      if (version === browseVersion.current) setBusy(false);
    }
  }
  async function send() {
    if (!selected || !location || !file || uploading) return;
    setUploading(true);
    setProgress(0);
    setError("");
    setConflict(false);
    const key = JSON.stringify([
      selected.id,
      selected.url,
      location.root,
      location.path,
      jpegName(name),
    ]);
    if (requestRef.current?.key !== key)
      requestRef.current = { key, id: crypto.randomUUID() };
    try {
      const info = await request<Info>(selected, "info", true);
      if (file.size > info.max_upload_bytes)
        throw new Error(
          `This server accepts pictures up to ${Math.floor(info.max_upload_bytes / 1024 / 1024)} MB. Choose a smaller picture.`,
        );
      const result = await upload(
        selected,
        file,
        name,
        location,
        requestRef.current.id,
        setProgress,
      );
      setReceipt(result);
      try {
        persist(
          servers.map((s) =>
            s.id === selected.id ? { ...s, last: location } : s,
          ),
        );
      } catch {
        /* Saved file is successful even if local storage is full. */
      }
    } catch (e) {
      setError((e as Error).message);
      if (e instanceof UploadError && e.status === 409) {
        setConflict(true);
        setStep(2);
      }
    } finally {
      setUploading(false);
    }
  }
  function reset() {
    setFile(null);
    setName("");
    setReceipt(null);
    setStep(1);
    setSelected(null);
    setLocation(null);
    setError("");
    setConflict(false);
    requestRef.current = null;
  }
  const picture =
    preview && !previewFailed ? (
      <img
        src={preview}
        alt="Your selected picture"
        onError={() => setPreviewFailed(true)}
      />
    ) : (
      <div className="preview-fallback">
        <ImagePlus />
        <span>{file?.name}</span>
        <small>
          Preview unavailable here. The listener will convert this picture.
        </small>
      </div>
    );
  return (
    <div className="app-page">
      <header className="app-header">
        <Wordmark />
        <button
          className="icon-button"
          aria-label="Server settings"
          disabled={uploading}
          onClick={() => {
            setSettings(true);
            setError("");
          }}
        >
          <Settings size={21} />
        </button>
      </header>
      <main className="phone-shell">
        {settings ? (
          <ServerSettings
            servers={servers}
            pairCode={pairCode}
            onPaired={() => setPairCode("")}
            onSave={persist}
            onClose={() => {
              setSettings(false);
              setSelected(null);
              setLocation(null);
              browseVersion.current++;
              setBusy(false);
              if (step === 3 && servers.length === 1)
                void browse(servers[0], servers[0].last || null);
            }}
          />
        ) : receipt ? (
          <section className="success">
            <div className="success-art">
              <img src="/brand/icon.svg" alt="" />
              <span>
                <Check size={22} />
              </span>
            </div>
            <span className="eyebrow">RIGHT WHERE IT BELONGS</span>
            <h1 ref={heading} tabIndex={-1}>
              Plunked.
            </h1>
            <p className="muted">One less thing between you and your work.</p>
            <div className="receipt">
              <Check size={20} />
              <div>
                <strong>{receipt.filename}</strong>
                <span>{receipt.server}</span>
                <small>{receipt.folder}</small>
                <small>
                  {receipt.width} × {receipt.height} ·{" "}
                  {Math.ceil(receipt.bytes / 1024)} KB · JPEG
                </small>
              </div>
            </div>
            <button className="button primary wide" onClick={reset}>
              Take another pic <Camera size={20} />
            </button>
          </section>
        ) : (
          <>
            <nav className="steps" aria-label="Upload steps">
              {(["Pic", "Name", "Location"] as const).map((label, index) => (
                <div
                  key={label}
                  className={
                    step === index + 1
                      ? "active"
                      : step > index + 1
                        ? "complete"
                        : ""
                  }
                  aria-current={step === index + 1 ? "step" : undefined}
                >
                  <span>
                    {step > index + 1 ? <Check size={13} /> : `0${index + 1}`}
                  </span>
                  {label}
                </div>
              ))}
            </nav>
            {step > 1 && (
              <button
                className="back"
                disabled={uploading || busy}
                onClick={() => {
                  if (step === 3) openName();
                  else setStep(1);
                  setError("");
                }}
              >
                <ArrowLeft size={16} /> Back
              </button>
            )}
            {step === 1 && (
              <section>
                <span className="eyebrow">FROM OUT THERE. TO RIGHT HERE.</span>
                <h1 ref={heading} tabIndex={-1}>
                  Start with
                  <br />a picture<span className="orange">.</span>
                </h1>
                <p className="muted">
                  The sketch. The setup. The thing that’s
                  <br className="desktop-break" /> easier to show than explain.
                </p>
                <input
                  ref={camera}
                  className="file-input"
                  type="file"
                  accept="image/*,.heic,.heif"
                  capture="environment"
                  aria-label="Take a picture"
                  onChange={(e) => {
                    chooseFile(e.target.files?.[0]);
                    e.target.value = "";
                  }}
                />
                <input
                  ref={library}
                  className="file-input"
                  type="file"
                  accept="image/*,.heic,.heif"
                  aria-label="Choose a picture"
                  onChange={(e) => {
                    chooseFile(e.target.files?.[0]);
                    e.target.value = "";
                  }}
                />
                {file ? (
                  <>
                    <div className="photo-preview">{picture}</div>
                    <button className="button primary wide" onClick={openName}>
                      Name it <ArrowRight size={20} />
                    </button>
                    <div className="two-actions">
                      <button
                        className="text-button"
                        onClick={() => camera.current?.click()}
                      >
                        Retake
                      </button>
                      <button
                        className="text-button"
                        onClick={() => library.current?.click()}
                      >
                        Choose another
                      </button>
                    </div>
                  </>
                ) : (
                  <>
                    <button
                      className="capture-card"
                      onClick={() => camera.current?.click()}
                    >
                      <span className="camera-circle">
                        <Camera size={36} strokeWidth={1.7} />
                      </span>
                      <strong>Take a pic</strong>
                      <span>Something worth bringing along.</span>
                      <span className="capture-plus">
                        <Plus size={19} />
                      </span>
                    </button>
                    <button
                      className="button secondary wide"
                      onClick={() => library.current?.click()}
                    >
                      <ImagePlus size={19} /> Choose from photos
                    </button>
                  </>
                )}
                <p className="app-footnote">
                  <span className="status-dot" /> Your picture goes straight to
                  your server.
                </p>
                {servers.length === 0 && (
                  <button
                    className="connect-first text-button"
                    onClick={() => setSettings(true)}
                  >
                    Connect a server <ArrowRight size={15} />
                  </button>
                )}
              </section>
            )}
            {step === 2 && (
              <section>
                <span className="eyebrow">MAKE IT MEAN SOMETHING</span>
                <h1 ref={heading} tabIndex={-1}>
                  Name it<span className="orange">.</span>
                </h1>
                <p className="muted">A good name saves a lot of explaining.</p>
                <div className="photo-preview compact">{picture}</div>
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    const issue = validateName(name);
                    setError(issue || "");
                    if (!issue) {
                      setConflict(false);
                      openLocation();
                    }
                  }}
                >
                  <label>
                    Picture name
                    <div className="filename-field">
                      <input
                        ref={nameInput}
                        enterKeyHint="next"
                        autoCorrect="off"
                        required
                        value={name}
                        onChange={(e) => {
                          setName(e.target.value);
                          setError("");
                        }}
                        placeholder="the-plan"
                        autoComplete="off"
                        autoCapitalize="none"
                      />
                      <span>.jpg</span>
                    </div>
                  </label>
                  <p className="fine-print">
                    Saved as an upright, high-quality JPEG. Original dimensions.
                    No GPS metadata.
                  </p>
                  {error && (
                    <p className="error" role="alert">
                      {error}
                    </p>
                  )}
                  {conflict && (
                    <button
                      type="button"
                      className="text-button"
                      onClick={() => {
                        setName((n) => n.replace(/\.jpe?g$/i, "") + "-2");
                        setConflict(false);
                        setError("");
                      }}
                    >
                      Use {name.replace(/\.jpe?g$/i, "")}-2.jpg
                    </button>
                  )}
                  <button className="button primary wide" type="submit">
                    Choose a location <ArrowRight size={20} />
                  </button>
                </form>
              </section>
            )}
            {step === 3 && (
              <section>
                <span className="eyebrow">GIVE IT A GOOD HOME</span>
                <h1 ref={heading} tabIndex={-1}>
                  {selected ? "Pick a folder" : "Choose a server"}
                  <span className="orange">.</span>
                </h1>
                <div className="file-chip">
                  {preview && !previewFailed ? (
                    <img src={preview} alt="" />
                  ) : (
                    <ImagePlus size={18} />
                  )}
                  <span>{jpegName(name)}</span>
                </div>
                {!selected ? (
                  <>
                    <div className="location-list">
                      {servers.map((s) => (
                        <button
                          key={s.id}
                          onClick={() => browse(s, s.last || null)}
                        >
                          <span className="list-icon">
                            <ServerIcon size={21} />
                          </span>
                          <span>
                            <strong>{s.name}</strong>
                            <small>{new URL(s.url).host}</small>
                          </span>
                          <ChevronRight size={20} />
                        </button>
                      ))}
                    </div>
                    {servers.length === 0 && (
                      <p className="muted">
                        Add your first server. Your picture will stay here while
                        you set it up.
                      </p>
                    )}
                    <button
                      className="button secondary wide"
                      onClick={() => setSettings(true)}
                    >
                      <Plus size={18} /> Add a server
                    </button>
                  </>
                ) : (
                  <>
                    <div className="folder-toolbar">
                      <span>
                        <ServerIcon size={17} />
                        {selected.name}
                      </span>
                      <button
                        disabled={uploading || busy}
                        className="text-button"
                        onClick={() => {
                          if (servers.length === 1) setSettings(true);
                          else {
                            setSelected(null);
                            setLocation(null);
                            setError("");
                          }
                        }}
                      >
                        {servers.length === 1 ? "Manage" : "Change"}
                      </button>
                    </div>
                    <div className="breadcrumb">
                      <Folder size={17} />
                      <span>
                        {location
                          ? [location.rootName, location.path]
                              .filter(Boolean)
                              .join(" / ")
                          : "Allowed folders"}
                      </span>
                    </div>
                    {location && (
                      <button
                        className="back folder-up"
                        disabled={uploading || busy}
                        onClick={() =>
                          browse(
                            selected,
                            location.path
                              ? {
                                  ...location,
                                  path: location.path
                                    .split("/")
                                    .slice(0, -1)
                                    .join("/"),
                                }
                              : null,
                          )
                        }
                      >
                        <ArrowLeft size={16} /> Up one folder
                      </button>
                    )}
                    {busy ? (
                      <div className="folder-loading" role="status">
                        <span className="loading-dot" /> Opening folders…
                      </div>
                    ) : (
                      <div
                        className="location-grid"
                        role="group"
                        aria-label="Folders"
                      >
                        {location
                          ? folders.map((folder) => (
                              <button
                                disabled={uploading}
                                key={folder}
                                onClick={() =>
                                  browse(selected, {
                                    ...location,
                                    path: [location.path, folder]
                                      .filter(Boolean)
                                      .join("/"),
                                  })
                                }
                              >
                                <span className="list-icon">
                                  <Folder size={21} />
                                </span>
                                <strong>{folder}</strong>
                                <small>
                                  Open folder <ArrowRight size={14} />
                                </small>
                              </button>
                            ))
                          : roots.map((root) => (
                              <button
                                key={root.id}
                                disabled={uploading}
                                onClick={() =>
                                  browse(selected, {
                                    root: root.id,
                                    rootName: root.name,
                                    path: "",
                                  })
                                }
                              >
                                <span className="list-icon">
                                  <Folder size={21} />
                                </span>
                                <strong>{root.name}</strong>
                                <small>
                                  Destination <ArrowRight size={14} />
                                </small>
                              </button>
                            ))}
                        {location && folders.length === 0 && (
                          <p className="empty-folder">
                            No subfolders. A good spot for this picture.
                          </p>
                        )}
                      </div>
                    )}
                    {error && (
                      <>
                        <p className="error" role="alert">
                          {error}
                        </p>
                        {!location && (
                          <button
                            className="text-button"
                            onClick={() => browse(selected, null)}
                          >
                            Browse from the top
                          </button>
                        )}
                      </>
                    )}
                    {location && (
                      <>
                        <button
                          disabled={busy || uploading}
                          className="button primary wide upload-button"
                          onClick={send}
                        >
                          {uploading
                            ? progress < 100
                              ? `Sending… ${progress}%`
                              : "Saving on your server…"
                            : "Plunk here"}
                          {!uploading && <ArrowRight size={20} />}
                        </button>
                        {uploading && (
                          <>
                            <progress
                              value={progress}
                              max={100}
                              aria-label="Upload progress"
                            />
                            <p className="fine-print" role="status">
                              Keep Plunk open until your picture arrives.
                            </p>
                          </>
                        )}
                      </>
                    )}
                  </>
                )}
              </section>
            )}
          </>
        )}
      </main>
      <div role="contentinfo" className="app-bottom">
        A little less friction. <span>A little more doing.</span>
      </div>
    </div>
  );
}
