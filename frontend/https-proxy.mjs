// HTTPS reverse proxy for Next.js dev server
// - Runs HTTPS on PORT_HTTPS (default 8080)
// - Proxies to Next dev (HTTP) on PORT_DEV (default 8081)
// Requires SSL_CERT_PATH and SSL_KEY_PATH

import fs from 'fs';
import { createServer } from 'https';
import httpProxy from 'http-proxy';
import { config as dotenvConfig } from 'dotenv';

// Load env (prefer .env.local in frontend)
dotenvConfig({ path: '.env.local' });
dotenvConfig();

const CERT = process.env.SSL_CERT_PATH;
const KEY = process.env.SSL_KEY_PATH;
const PORT_HTTPS = Number(process.env.PORT_HTTPS || 8080);
const PORT_DEV = Number(process.env.PORT_DEV || 8081);
const TARGET = `http://127.0.0.1:${PORT_DEV}`;

if (!CERT || !KEY) {
  console.error('Missing SSL_CERT_PATH or SSL_KEY_PATH.');
  console.error('Set them in frontend/.env.local and try again.');
  process.exit(1);
}

if (!fs.existsSync(CERT) || !fs.existsSync(KEY)) {
  console.error('SSL cert or key file not found.');
  console.error(`CERT: ${CERT} exists=${fs.existsSync(CERT)}`);
  console.error(`KEY : ${KEY} exists=${fs.existsSync(KEY)}`);
  console.error('Generate dev certs (e.g., mkcert) and update paths.');
  process.exit(1);
}

const options = {
  cert: fs.readFileSync(CERT),
  key: fs.readFileSync(KEY),
};

const proxy = httpProxy.createProxyServer({
  target: TARGET,
  changeOrigin: false,
  ws: true,
  secure: false,
  xfwd: true,
  autoRewrite: true,
  protocolRewrite: 'https'
});
proxy.on('error', (err, req, res) => {
  console.error('Proxy error:', err?.message || err);
  if (!res.headersSent) {
    res.writeHead(502);
  }
  res.end('Proxy error');
});

const server = createServer(options, (req, res) => {
  // Preserve original host/scheme for downstream and redirects
  req.headers['x-forwarded-proto'] = 'https';
  if (req.headers.host) {
    req.headers['x-forwarded-host'] = req.headers.host;
    const m = String(req.headers.host).match(/:(\d+)$/);
    const inboundPort = m ? m[1] : '443';
    req.headers['x-forwarded-port'] = inboundPort;
  } else if (process.env.PORT_HTTPS) {
    req.headers['x-forwarded-port'] = String(process.env.PORT_HTTPS);
  }
  proxy.web(req, res, { target: TARGET });
});

server.on('upgrade', (req, socket, head) => {
  proxy.ws(req, socket, head, { target: TARGET });
});

// Rewrite absolute redirects from Next dev (localhost:8081) to the external host
proxy.on('proxyRes', (proxyRes, req, res) => {
  const host = req.headers['x-forwarded-host'] || req.headers.host;
  const location = proxyRes.headers && proxyRes.headers.location;
  if (host && location) {
    try {
      const url = new URL(location, `http://${host}`);
      const isLocalTarget = /^(localhost|127\.0\.0\.1)(:8081)?$/i.test(url.host);
      if (isLocalTarget) {
        const external = `https://${host}${url.pathname}${url.search}${url.hash}`;
        proxyRes.headers.location = external;
      }
    } catch {}
  }
});

server.listen(PORT_HTTPS, '0.0.0.0', () => {
  console.log(`HTTPS proxy listening on https://0.0.0.0:${PORT_HTTPS} -> ${TARGET}`);
});
