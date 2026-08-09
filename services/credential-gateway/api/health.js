// GET /api/health — sır içermeyen canlılık ucu.
export default function handler(req, res) {
  res.statusCode = req.method === "GET" ? 200 : 405;
  res.setHeader("Content-Type", "application/json");
  res.setHeader("Cache-Control", "no-store");
  res.end(JSON.stringify({
    ok: req.method === "GET",
    service: "lumos-credential-gateway",
    schema: "lumos-credential-v2",
  }));
}
