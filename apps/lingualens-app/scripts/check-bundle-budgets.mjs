import { gzipSync } from "node:zlib";
import { readFile, readdir } from "node:fs/promises";
import { spawn } from "node:child_process";
import { createServer } from "node:net";
import path from "node:path";
import process from "node:process";

/**
 * Next.js 16 no longer prints the `Size` and `First Load JS` columns: its
 * `printTreeView` rows carry only the route, `Revalidate`, and `Expire`, so
 * there is no longer any build-log text to parse (Next.js <= 15 was scraped
 * before). This check therefore measures the budgets directly from the build:
 *
 * - shared: `polyfillFiles` + `rootMainFiles` in `.next/build-manifest.json`.
 *   That set is exactly the intersection of the chunks every prerendered route
 *   references, so it is the JavaScript loaded by all routes.
 * - per route: every `<script src>` in the HTML the built server serves for
 *   that route, gzip summed. That is what a browser downloads before the route
 *   is interactive, and it covers dynamic routes that have no prerendered HTML.
 *
 * Every budgeted route must be measurable. A route that cannot be measured is a
 * failure, never a skip, so the gate cannot silently degrade.
 */

const projectRoot = process.cwd();
const distDir = path.join(projectRoot, ".next");
const manifestPath = path.join(distDir, "build-manifest.json");
const budgetPath = path.join(projectRoot, "bundle-budgets.json");
const chunkRoot = path.join(distDir, "static/chunks");
const nextBin = path.join(projectRoot, "node_modules", "next", "dist", "bin", "next");
const requestTimeoutMs = 30_000;
const readinessTimeoutMs = 60_000;
// Route patterns such as `/sessions/[sessionId]` need a concrete value to be
// requested. The script tags a route renders are determined by its module
// graph, not by the fetched record, so a placeholder measures the same chunks.
const paramPlaceholder = "budget-probe";

const [rawBudgets, rawManifest] = await Promise.all([
  readFile(budgetPath, "utf8").catch(() => {
    throw new Error(`Missing ${path.relative(projectRoot, budgetPath)}.`);
  }),
  readFile(manifestPath, "utf8").catch(() => {
    throw new Error(`Missing ${path.relative(projectRoot, manifestPath)}; run "npm run build" first.`);
  }),
]);
const budgets = JSON.parse(rawBudgets);
const manifest = JSON.parse(rawManifest);
if (!budgets.routes || Object.keys(budgets.routes).length === 0) {
  throw new Error(`${path.relative(projectRoot, budgetPath)} declares no route budgets; nothing would be enforced.`);
}

const failures = [];
const sizeCache = new Map();
let activeChild = null;

for (const signal of ["SIGINT", "SIGTERM"]) {
  process.once(signal, () => {
    activeChild?.kill("SIGKILL");
    process.exit(130);
  });
}

const sharedChunks = [...(manifest.polyfillFiles ?? []), ...(manifest.rootMainFiles ?? [])]
  .filter((file) => file.endsWith(".js"));

if (sharedChunks.length === 0) {
  failures.push("No shared chunks were found in .next/build-manifest.json.");
}

async function gzipKb(relativePath) {
  const cached = sizeCache.get(relativePath);
  if (cached !== undefined) return cached;
  const bytes = await readFile(path.join(distDir, relativePath));
  const kb = gzipSync(bytes).byteLength / 1024;
  sizeCache.set(relativePath, kb);
  return kb;
}

async function sumGzipKb(relativePaths) {
  const sizes = await Promise.all(relativePaths.map(gzipKb));
  return sizes.reduce((total, size) => total + size, 0);
}

const sharedKb = await sumGzipKb(sharedChunks);
console.log(`shared First Load JS: ${sharedKb.toFixed(1)} kB / ${budgets.sharedFirstLoadKb} kB`);
if (sharedKb > budgets.sharedFirstLoadKb) {
  failures.push(
    `Shared First Load JS is ${sharedKb.toFixed(1)} kB; budget is ${budgets.sharedFirstLoadKb} kB.`,
  );
}

const measurements = new Map();
const server = await startServer();
try {
  for (const [route, budget] of Object.entries(budgets.routes)) {
    const measured = await measureRoute(server.origin, route);
    if (measured.error) {
      failures.push(`Route ${route} could not be measured: ${measured.error}`);
      continue;
    }
    measurements.set(route, measured);
    console.log(`${route}: ${measured.kb.toFixed(1)} kB / ${budget} kB`);

    const missingShared = sharedChunks.filter((chunk) => !measured.chunks.has(chunk));
    if (missingShared.length > 0) {
      failures.push(
        `Route ${route} does not reference shared chunk(s) ${missingShared.join(", ")}; ` +
          "the shared baseline and the served HTML disagree.",
      );
    }
    if (measured.kb > budget) {
      failures.push(`${route} is ${measured.kb.toFixed(1)} kB; budget is ${budget} kB.`);
    }
  }
} finally {
  await server.stop();
}

// Next emits lazily loaded client chunks as `<id>.<content-hash>.js`.
// Hyphenated files are framework, shared, layout, or route entry chunks and
// are already governed by the shared/route First Load budgets above.
const chunkFiles = (await listJavaScriptFiles(chunkRoot)).filter((filePath) => (
  /^\d+\.[A-Za-z0-9]+\.js$/.test(path.basename(filePath))
));
const chunkMeasurements = await Promise.all(chunkFiles.map(async (filePath) => ({
  filePath,
  gzipKb: gzipSync(await readFile(filePath)).byteLength / 1024,
})));
chunkMeasurements.sort((left, right) => right.gzipKb - left.gzipKb);

for (const chunk of chunkMeasurements.slice(0, 10)) {
  const relativePath = path.relative(projectRoot, chunk.filePath);
  console.log(`${relativePath}: ${chunk.gzipKb.toFixed(1)} kB gzip`);
}

const oversizedChunks = chunkMeasurements.filter((chunk) => chunk.gzipKb > budgets.maxNewClientChunkKb);
for (const chunk of oversizedChunks) {
  failures.push(`${path.relative(projectRoot, chunk.filePath)} is ${chunk.gzipKb.toFixed(1)} kB gzip; client chunk budget is ${budgets.maxNewClientChunkKb} kB.`);
}

if (failures.length) {
  console.error("\nBundle budget verification failed:");
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log(`Bundle budget verification passed (${measurements.size} routes).`);

async function measureRoute(origin, routePattern) {
  const requestPath = routePattern.replace(/\[[^\]]+\]/g, paramPlaceholder);
  let response;
  try {
    response = await fetch(`${origin}${requestPath}`, {
      redirect: "manual",
      signal: AbortSignal.timeout(requestTimeoutMs),
    });
  } catch (error) {
    return { error: `${requestPath} did not respond (${error.message})` };
  }
  if (response.status !== 200) {
    return { error: `${requestPath} returned HTTP ${response.status}` };
  }
  const html = await response.text();
  const chunks = new Set();
  for (const match of html.matchAll(/src="\/_next\/(static\/chunks\/[^"]+)"/g)) {
    chunks.add(decodeURIComponent(match[1]));
  }
  if (chunks.size === 0) {
    return { error: `${requestPath} returned no client script tags` };
  }
  return { chunks, kb: await sumGzipKb([...chunks]) };
}

async function startServer() {
  let lastError;
  for (let attempt = 0; attempt < 3; attempt += 1) {
    const port = await findFreePort();
    const origin = `http://127.0.0.1:${port}`;
    const child = spawn(
      process.execPath,
      [nextBin, "start", "--hostname", "127.0.0.1", "--port", String(port)],
      { cwd: projectRoot, stdio: ["ignore", "pipe", "pipe"] },
    );
    activeChild = child;
    const output = [];
    const record = (data) => {
      output.push(data.toString());
      if (output.length > 40) output.shift();
    };
    child.stdout.on("data", record);
    child.stderr.on("data", record);

    let exited = null;
    child.once("exit", (code, signal) => {
      exited = `exit code ${code ?? `signal ${signal}`}`;
    });

    const deadline = Date.now() + readinessTimeoutMs;
    let ready = false;
    while (Date.now() < deadline) {
      if (exited) break;
      try {
        const probe = await fetch(`${origin}/login`, {
          redirect: "manual",
          signal: AbortSignal.timeout(5_000),
        });
        if (probe.status < 500) {
          ready = true;
          break;
        }
      } catch {
        // Server not listening yet.
      }
      await new Promise((resolve) => setTimeout(resolve, 250));
    }

    if (ready) {
      return {
        origin,
        stop: () => stopServer(child),
      };
    }

    await stopServer(child);
    lastError = exited ?? "timed out waiting for the server to become ready";
    console.warn(`Notice: attempt ${attempt + 1} to start the built server failed (${lastError}).`);
    if (output.length) console.warn(output.join("").trim());
  }
  throw new Error(`Could not start the built server: ${lastError}`);
}

async function stopServer(child) {
  activeChild = null;
  if (child.exitCode !== null || child.signalCode !== null) return;
  const stopped = new Promise((resolve) => child.once("exit", resolve));
  child.kill("SIGTERM");
  const timer = setTimeout(() => child.kill("SIGKILL"), 5_000);
  timer.unref();
  await stopped;
  clearTimeout(timer);
}

async function findFreePort() {
  return new Promise((resolve, reject) => {
    const probe = createServer();
    probe.unref();
    probe.once("error", reject);
    probe.listen(0, "127.0.0.1", () => {
      const address = probe.address();
      probe.close(() => resolve(address.port));
    });
  });
}

async function listJavaScriptFiles(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const nested = await Promise.all(entries.map((entry) => {
    const entryPath = path.join(directory, entry.name);
    if (entry.isDirectory()) return listJavaScriptFiles(entryPath);
    return entry.isFile() && entry.name.endsWith(".js") ? [entryPath] : [];
  }));
  return nested.flat();
}
