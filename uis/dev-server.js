const http = require("node:http");
const fs = require("node:fs");
const path = require("node:path");
const { URL } = require("node:url");

const port = Number(process.env.PORT || 3000);
const staticRoot = path.resolve(__dirname, process.env.STATIC_DIR || "website");
const backendUrl = new URL(process.env.BACKEND_URL || "http://backend:8010");

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
  const filePath = path.resolve(staticRoot, `.${requestPath === "/" ? "/index.html" : requestPath}`);
  if (!filePath.startsWith(staticRoot)) {
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
    response.writeHead(200);
    fs.createReadStream(filePath).pipe(response);
  });
}

http.createServer((request, response) => {
  if (request.url.startsWith("/api") || request.url === "/health") {
    proxy(request, response);
    return;
  }
  serveStatic(request, response);
}).listen(port, "0.0.0.0", () => console.log(`Serving ${staticRoot} on ${port}; backend proxy: ${backendUrl.host}`));