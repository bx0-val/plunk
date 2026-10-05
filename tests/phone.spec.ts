import { test, expect, type Page } from "@playwright/test";

const server = {
  id: "home",
  name: "Home lab",
  url: "https://lab.example",
  auth: "bearer",
  token: "test",
  username: "",
  password: "",
};
const photo = {
  name: "test.png",
  mimeType: "image/png",
  buffer: Buffer.from(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a9l8AAAAASUVORK5CYII=",
    "base64",
  ),
};

async function start(page: Page, servers: object[] = [server]) {
  await page.addInitScript(
    (value) => localStorage.setItem("plunk.servers.v1", JSON.stringify(value)),
    servers,
  );
  await page.route("https://lab.example/api/v1/**", async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname.endsWith("/info"))
      return route.fulfill({
        json: {
          name: "Home lab",
          auth: "bearer",
          version: 1,
          max_upload_bytes: 25 * 1024 ** 2,
        },
      });
    return route.fulfill({
      json: url.searchParams.has("root")
        ? { directories: ["Whiteboards", "Hardware"] }
        : {
            roots: [
              { id: "projects", name: "Projects" },
              { id: "notes", name: "Notes" },
            ],
          },
    });
  });
  await page.goto("/app");
  await page
    .getByLabel("Choose a picture", { exact: true })
    .setInputFiles(photo);
  await page.getByRole("button", { name: "Name it", exact: true }).click();
  await expect(
    page.getByRole("textbox", { name: "Picture name" }),
  ).toBeFocused();
  const preview = await page.locator(".photo-preview").boundingBox();
  const picture = await page.locator(".photo-preview img").boundingBox();
  expect(picture!.height).toBeLessThanOrEqual(preview!.height);
  await page.getByRole("textbox", { name: "Picture name" }).fill("the-plan");
  await page.getByRole("button", { name: "Choose a location" }).click();
}

test("one server opens a two-column folder grid; back focuses the name", async ({
  page,
}) => {
  await start(page);
  await expect(
    page.getByRole("heading", { name: "Pick a folder." }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Choose a server." }),
  ).toHaveCount(0);
  const a = page.getByRole("button", { name: "Projects Destination" });
  const b = page.getByRole("button", { name: "Notes Destination" });
  const first = await a.boundingBox();
  const second = await b.boundingBox();
  expect(first!.y).toBe(second!.y);
  expect(second!.x).toBeGreaterThan(first!.x + first!.width);
  expect(first!.height).toBeGreaterThanOrEqual(44);
  await a.click();
  await expect(
    page.getByRole("button", { name: "Whiteboards Open folder" }),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Plunk here" })).toBeVisible();
  await page.getByRole("button", { name: "Back", exact: true }).click();
  await expect(
    page.getByRole("textbox", { name: "Picture name" }),
  ).toBeFocused();
  await expect(page.getByRole("textbox", { name: "Picture name" })).toHaveValue(
    "the-plan",
  );
});

test("multiple servers keep the choice, and the last folder is reused", async ({
  page,
}) => {
  await start(page, [
    {
      ...server,
      last: { root: "projects", rootName: "Projects", path: "work" },
    },
    { ...server, id: "studio", name: "Studio" },
  ]);
  await expect(
    page.getByRole("heading", { name: "Choose a server." }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Home lab lab.example" }).click();
  await expect(page.locator(".breadcrumb")).toContainText("Projects / work");
  await page.getByRole("button", { name: "Change", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Choose a server." }),
  ).toBeVisible();
});

test("first server setup returns directly to folders and keeps the picture", async ({
  page,
}) => {
  await start(page, []);
  await page.getByRole("button", { name: "Add a server" }).click();
  await page.getByRole("button", { name: "Use an address" }).click();
  await page.getByRole("textbox", { name: "HTTPS address" }).fill(server.url);
  await page
    .getByRole("button", { name: "Connect to server", exact: true })
    .click();
  await page.getByLabel("Secret token", { exact: true }).fill("test");
  await page.getByRole("button", { name: "Test & save server" }).click();
  await expect(page.getByRole("status")).toContainText("connected and saved");
  await page.getByRole("button", { name: "Close settings" }).click();
  await expect(
    page.getByRole("button", { name: "Projects Destination" }),
  ).toBeVisible();
  await expect(page.locator(".file-chip")).toContainText("the-plan.jpg");
});

test("lost upload response retains name, picture and request ID for retry", async ({
  page,
}) => {
  await start(page);
  await page.getByRole("button", { name: "Projects Destination" }).click();
  const ids: string[] = [];
  await page.route("https://lab.example/api/v1/uploads", async (route) => {
    const body = route.request().postDataBuffer()!.toString();
    ids.push(body.match(/name="request_id"\r\n\r\n([^\r]+)/)![1]);
    if (ids.length === 1) return route.abort("failed");
    return route.fulfill({
      json: {
        server: "Home lab",
        folder: "Projects",
        filename: "the-plan.jpg",
        bytes: 1234,
        width: 1,
        height: 1,
        request_id: ids[0],
      },
    });
  });
  await page.getByRole("button", { name: "Plunk here" }).click();
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(page.locator(".file-chip img")).toBeVisible();
  await page.getByRole("button", { name: "Plunk here" }).click();
  await expect(page.getByRole("heading", { name: "Plunked." })).toBeVisible();
  expect(ids).toHaveLength(2);
  expect(ids[0]).toBe(ids[1]);
});

test("standalone pairing is consumed once, including reopening settings", async ({
  page,
}) => {
  let calls = 0;
  await page.addInitScript(() =>
    Object.defineProperty(navigator, "standalone", { value: true }),
  );
  await page.route("**/api/v1/pair", (route) => {
    calls++;
    return route.fulfill({
      json: { name: "Home lab", token: "test-credential" },
    });
  });
  // Pairing must persist the returned token even if a later directory request fails.
  await page.route("**/api/v1/directories", (route) => route.abort());
  await page.goto("/app#pair=123456");
  await expect(
    page.getByRole("heading", { name: "You’re connected." }),
  ).toBeVisible();
  await expect(page).toHaveURL(/\/app$/);
  await page.getByRole("button", { name: "Let’s Plunk" }).click();
  await page.getByRole("button", { name: "Server settings" }).click();
  await expect(page.getByRole("textbox", { name: "Pairing code" })).toHaveValue(
    "",
  );
  expect(calls).toBe(1);
  expect(
    await page.evaluate(
      () => JSON.parse(localStorage.getItem("plunk.servers.v1")!)[0].token,
    ),
  ).toBe("test-credential");
});

test("Safari pairing asks for an explicit tap before consuming the code", async ({
  page,
}) => {
  let calls = 0;
  await page.route("**/api/v1/pair", (route) => {
    calls++;
    return route.fulfill({ json: { name: "Home lab", token: "test" } });
  });
  await page.goto("/app#pair=123456");
  await expect(
    page.getByText(/add Plunk to your Home Screen first/),
  ).toBeVisible();
  expect(calls).toBe(0);
  await page.getByRole("button", { name: "Connect this server" }).click();
  await expect(
    page.getByRole("heading", { name: "You’re connected." }),
  ).toBeVisible();
  expect(calls).toBe(1);
});

test("narrow screens keep folders within the viewport and respect reduced motion", async ({
  page,
}) => {
  await page.setViewportSize({ width: 320, height: 740 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await start(page);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await expect(page.locator("html")).toHaveCSS("scroll-behavior", "auto");
  await expect(page.locator(":root")).toHaveCSS("color-scheme", "dark");
  const button = page.getByRole("button", { name: "Projects Destination" });
  await expect(button).toHaveCSS("transition-duration", "0s");
});
