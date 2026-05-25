/**
 * Writes frontend/config.js from GIVEFUND_API_URL (Vercel / Netlify build).
 */
const fs = require("fs");
const path = require("path");

const apiUrl = process.env.GIVEFUND_API_URL || "http://localhost:8000";
const out = path.join(__dirname, "..", "frontend", "config.js");
const body = `window.GIVEFUND_API_URL = "${apiUrl.replace(/"/g, '\\"')}";\n`;

fs.writeFileSync(out, body);
console.log("Wrote", out, "->", apiUrl);
