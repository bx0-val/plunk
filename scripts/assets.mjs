import sharp from "sharp";
import { mkdir, readFile, access } from "node:fs/promises";
await mkdir("public/brand", { recursive: true });
await mkdir("public/launch", { recursive: true });
await mkdir(".local", { recursive: true });
for (const [name, size] of [
  ["icon-192.png", 192],
  ["icon-512.png", 512],
  ["apple-touch-icon.png", 180],
]) {
  await sharp("public/brand/icon.svg")
    .resize(size, size)
    .png()
    .toFile(`public/brand/${name}`);
}
// Original test fixture, deliberately labeled. Not represented as a camera photograph.
const fixture = `<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="900"><rect width="1200" height="900" fill="#dedacf"/><rect x="65" y="65" width="1070" height="770" rx="12" fill="#acb0a6"/><rect x="85" y="85" width="1030" height="730" fill="#f6f6eb"/><g font-family="Segoe Print,Comic Sans MS,cursive" fill="#354b44"><text x="160" y="225" font-size="68">the next big thing</text><g fill="none" stroke="#486457" stroke-width="5"><rect x="170" y="320" width="310" height="180" rx="10"/><path d="M530 410h150m-25-25 28 25-28 25"/><ellipse cx="850" cy="410" rx="125" ry="100"/></g><text x="224" y="428" font-size="51">an idea</text><text x="779" y="400" font-size="40">make it</text><text x="809" y="453" font-size="40">real</text><text x="188" y="624" font-size="48">less friction.</text><text x="188" y="693" font-size="48">more doing.</text><path d="M182 713q180-19 360-5" stroke="#f56532" stroke-width="7" fill="none"/><text x="867" y="692" font-size="120" fill="#f56532">✳</text></g><text x="91" y="870" font-family="Arial" font-size="18" fill="#666358">PLUNK · GENERATED WHITEBOARD TEST FIXTURE</text></svg>`;
await sharp(Buffer.from(fixture))
  .jpeg({ quality: 95 })
  .toFile(".local/whiteboard.jpg");
const social = `<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630"><rect width="1200" height="630" fill="#faf7f0"/><circle cx="1100" cy="80" r="470" fill="#f56532"/><g fill="#20201e" font-family="Arial,sans-serif"><text x="70" y="112" font-size="66" font-weight="900" letter-spacing="-4">plunk<tspan fill="#f56532">.</tspan></text><text x="70" y="260" font-size="68" font-weight="800" letter-spacing="-3">Your camera.</text><text x="70" y="337" font-size="68" font-weight="800" letter-spacing="-3">Your folders.</text><text x="70" y="414" font-size="68" font-weight="800" fill="#bd481f" letter-spacing="-3">Plunk.</text><text x="74" y="536" font-size="25">Pic → Name → Location</text></g></svg>`;
const layers = [];
try {
  await access("public/launch/app-success.png");
  layers.push({
    input: await sharp("public/launch/app-success.png")
      .resize({ height: 554 })
      .png()
      .toBuffer(),
    left: 805,
    top: 38,
  });
} catch {
  /* Initial asset generation precedes the actual browser capture. */
}
await sharp(Buffer.from(social))
  .composite(layers)
  .png()
  .toFile("public/brand/social.png");
console.log("Plunk icons, fixture, and social graphic generated.");
