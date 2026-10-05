export type AuthMode = "none" | "bearer" | "basic";
export type Location = { root: string; path: string; rootName: string };
export type Server = {
  id: string;
  name: string;
  url: string;
  auth: AuthMode;
  token: string;
  username: string;
  password: string;
  last?: Location;
};
export type Info = {
  name: string;
  auth: AuthMode;
  max_upload_bytes: number;
  version: number;
};
export type Receipt = {
  server: string;
  folder: string;
  filename: string;
  bytes: number;
  width: number;
  height: number;
  request_id: string;
};
const storageKey = "plunk.servers.v1";
export function loadServers(): Server[] {
  try {
    const data: unknown = JSON.parse(localStorage.getItem(storageKey) || "[]");
    if (!Array.isArray(data)) return [];
    return data.filter(
      (s): s is Server =>
        s &&
        ["id", "name", "url", "token", "username", "password"].every(
          (k) => typeof s[k] === "string",
        ) &&
        ["none", "basic", "bearer"].includes(s.auth),
    );
  } catch {
    return [];
  }
}
export function saveServers(servers: Server[]) {
  localStorage.setItem(storageKey, JSON.stringify(servers));
}
export function normalizeUrl(value: string) {
  const url = new URL(value.trim());
  const loopback = ["localhost", "127.0.0.1", "[::1]"].includes(url.hostname);
  if (url.protocol !== "https:" && !(url.protocol === "http:" && loopback))
    throw new Error(
      "Use an HTTPS address with a certificate trusted by this phone.",
    );
  if (url.username || url.password || url.search || url.hash)
    throw new Error(
      "Enter an address without credentials, a query, or a fragment.",
    );
  return url.href.replace(/\/$/, "");
}
export function headers(server: Server): Record<string, string> {
  if (server.auth === "bearer")
    return { Authorization: `Bearer ${server.token}` };
  if (server.auth === "basic") {
    const bytes = new TextEncoder().encode(
      `${server.username}:${server.password}`,
    );
    return {
      Authorization: `Basic ${btoa(Array.from(bytes, (b) => String.fromCharCode(b)).join(""))}`,
    };
  }
  return {};
}
export async function request<T>(
  server: Server,
  endpoint: string,
  publicRequest = false,
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${server.url}/api/v1/${endpoint}`, {
      headers: publicRequest ? {} : headers(server),
      credentials: "omit",
      redirect: "error",
      signal: AbortSignal.timeout(15000),
      cache: "no-store",
    });
  } catch {
    throw new Error(
      "Couldn’t reach this server. Check its address, HTTPS certificate, and allowed app origin. Your picture is still here.",
    );
  }
  const body = await response.json().catch(() => null);
  if (!response.ok)
    throw new Error(
      typeof body?.detail === "string"
        ? body.detail
        : "The server could not complete this request.",
    );
  if (!body) throw new Error("This address did not return a Plunk response.");
  return body as T;
}
export function validateName(value: string): string | null {
  const base = value
    .trim()
    .normalize("NFC")
    .replace(/\.jpe?g$/i, "");
  if (
    !base ||
    base === "." ||
    base === ".." ||
    /[/\\\u0000-\u001f\u007f-\u009f]/u.test(base)
  )
    return "Enter a name without slashes or control characters.";
  if (new TextEncoder().encode(`${base}.jpg`).length > 240)
    return "That name is too long. Try a shorter one.";
  return null;
}
export const jpegName = (name: string) =>
  name
    .trim()
    .normalize("NFC")
    .replace(/\.jpe?g$/i, "") + ".jpg";
export class UploadError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}
export function upload(
  server: Server,
  file: File,
  name: string,
  location: Location,
  id: string,
  progress: (value: number) => void,
): Promise<Receipt> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${server.url}/api/v1/uploads`);
    xhr.timeout = 180000;
    for (const [key, value] of Object.entries(headers(server)))
      xhr.setRequestHeader(key, value);
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable)
        progress(Math.round((event.loaded / event.total) * 100));
    };
    xhr.onerror = () =>
      reject(
        new UploadError(
          "Connection lost. Your picture is still here. Retry to check whether it arrived.",
          0,
        ),
      );
    xhr.ontimeout = () =>
      reject(
        new UploadError(
          "The server took too long. Retry safely to check whether your picture arrived.",
          0,
        ),
      );
    xhr.onload = () => {
      let body;
      try {
        body = JSON.parse(xhr.responseText);
      } catch {
        reject(
          new UploadError(
            "The server returned an unexpected response. Your picture is still here.",
            xhr.status,
          ),
        );
        return;
      }
      if (xhr.status >= 200 && xhr.status < 300) resolve(body);
      else
        reject(
          new UploadError(
            typeof body.detail === "string"
              ? body.detail
              : "Could not save the picture. Check your filename and location.",
            xhr.status,
          ),
        );
    };
    const form = new FormData();
    form.append("image", file);
    form.append("name", name);
    form.append("root", location.root);
    form.append("path", location.path);
    form.append("request_id", id);
    xhr.send(form);
  });
}
