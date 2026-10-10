const http = require("node:http");
const fs = require("node:fs");
const path = require("node:path");
const { URL } = require("node:url");

const port = Number(process.env.PORT || 3000);
const staticRoot = path.resolve(__dirname, process.env.STATIC_DIR || "website");
const sharedRoot = path.resolve(__dirname, "shared");
const backendUrl = new URL(process.env.BACKEND_URL || "http://backend:8010");

function getContentType(filePath) {
  const extension = path.extname(filePath).toLowerCase();

  const mimeTypes = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".ico": "image/x-icon",
    ".webp": "image/webp",
    ".wasm": "application/wasm",
  };

  return mimeTypes[extension] || "application/octet-stream";
}

function proxy(request, response) {
  const upstream = http.request(
    { hostname: backendUrl.hostname, port: backendUrl.port, method: request.method, path: request.url, headers: request.headers },
    (upstreamResponse) => {
      response.writeHead(upstreamResponse.statusCode || 502, upstreamResponse.headers);
      upstreamResponse.pipe(response);
    },
  );
  upstream.on("error", () => {
    response.writeHead(502, { "Content-Type": "application/json" });
    response.end(JSON.stringify({ detail: "El backend no está disponible." }));
  });
  request.pipe(upstream);
}

function serveStatic(request, response) {
  const requestPath = decodeURIComponent(new URL(request.url, "http://localhost").pathname);
  const normalizedPath = requestPath === "/" ? "/index.html" : requestPath;
  const isSharedAsset = normalizedPath.startsWith("/shared/");
  const baseRoot = isSharedAsset ? sharedRoot : staticRoot;
  const relativePath = isSharedAsset ? normalizedPath.replace(/^\/shared/, "") || "/" : normalizedPath;
  const filePath = path.resolve(baseRoot, `.${relativePath === "/" ? "/index.html" : relativePath}`);
  const allowedRoots = [staticRoot, sharedRoot];
  if (!allowedRoots.some((root) => filePath.startsWith(root))) {
    response.writeHead(400);
    response.end("Solicitud inválida.");
    return;
  }
  fs.stat(filePath, (error, stat) => {
    if (error || !stat.isFile()) {
      response.writeHead(404);
      response.end("No encontrado.");
      return;
    }
    response.writeHead(200, { "Content-Type": getContentType(filePath) });
    fs.createReadStream(filePath).pipe(response);
  });
}

function createServer() {
  return http.createServer((request, response) => {
    if (request.url.startsWith("/api") || request.url === "/health") {
      proxy(request, response);
      return;
    }
    serveStatic(request, response);
  });
}

if (require.main === module) {
  createServer().listen(port, "0.0.0.0", () => console.log(`Serving ${staticRoot} on ${port}; backend proxy: ${backendUrl.host}`));
}

module.exports = { getContentType, createServer };