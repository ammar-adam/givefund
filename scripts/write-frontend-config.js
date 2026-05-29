/**
 * Writes frontend/config.js from env (Vercel / Netlify build).
 * GIVEFUND_API_URL — required in production
 * GIVEFUND_FRONTEND_URL — optional; auto-detected on Vercel when unset
 */
const fs = require("fs");
const path = require("path");

const apiUrl = process.env.GIVEFUND_API_URL || "http://localhost:8000";
const frontendUrl =
  process.env.GIVEFUND_FRONTEND_URL ||
  (process.env.VERCEL_URL ? `https://${process.env.VERCEL_URL}` : "") ||
  process.env.URL ||
  "";

const lines = [
  `window.GIVEFUND_API_URL = "${apiUrl.replace(/"/g, '\\"')}";`,
];
if (frontendUrl && !frontendUrl.includes("localhost")) {
  const fe = frontendUrl.startsWith("http") ? frontendUrl : `https://${frontendUrl}`;
  lines.push(`window.GIVEFUND_FRONTEND_URL = "${fe.replace(/"/g, '\\"')}";`);
}

const out = path.join(__dirname, "..", "frontend", "config.js");
fs.writeFileSync(out, lines.join("\n") + "\n");
console.log("Wrote", out, "-> API", apiUrl, frontendUrl ? `frontend ${frontendUrl}` : "");
