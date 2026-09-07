import { execFileSync } from "node:child_process";
import { fileURLToPath, pathToFileURL } from "node:url";
import { existsSync } from "node:fs";
import path from "node:path";

const dir = path.dirname(fileURLToPath(import.meta.url));
const html = path.join(dir, "EduMind_Teacher_Frontend_Final.html");
const pdf = path.join(dir, "EduMind_Teacher_Frontend_Final.pdf");
const chrome = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";

execFileSync(chrome, [
  "--headless=new",
  "--disable-gpu",
  "--no-pdf-header-footer",
  "--hide-scrollbars",
  "--virtual-time-budget=15000",
  `--print-to-pdf=${pdf}`,
  pathToFileURL(html).href,
], { stdio: "inherit" });

if (!existsSync(pdf)) throw new Error("PDF was not created");
console.log("OK", pdf);
