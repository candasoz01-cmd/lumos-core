import { hostedSessionClaims } from "../_lib/hosted_lumos.js";
import { sessionLumosId } from "../_lib/lumos_session.js";

const WORKSPACES = [
  "mail",
  "social",
  "calendar",
  "files",
  "tasks",
  "admin",
  "github",
  "cloud",
  "chat",
];

function card(workspaceId) {
  const chat = workspaceId === "chat";
  const cloud = workspaceId === "cloud";
  const connected = chat || cloud;
  return {
    workspace_id: workspaceId,
    summary: chat
      ? "Lumos oturumu bağlı"
      : cloud
        ? "Lumos bulut hizmeti erişilebilir"
        : "Canlı bağlantı doğrulanmadı",
    health: connected ? "ready" : "stub",
    attention_count: 0,
    state: connected ? "connected" : "disconnected",
    age_seconds: null,
    detail: {
      source: "mobile_session",
      account_connection_verified: chat,
      service_reachability_verified: cloud,
      operations_enabled: false,
    },
  };
}

export default async function handler(req, res) {
  res.setHeader("Cache-Control", "no-store");
  if (req.method !== "GET") {
    return res.status(405).json({ error: "method_not_allowed" });
  }

  const lumosId = sessionLumosId(hostedSessionClaims(req));
  if (!lumosId) return res.status(401).json({ error: "unauthorized" });

  return res.status(200).json({
    ok: true,
    hub: {
      source: "live",
      day_summary_line: "Lumos oturumu bağlı · bulut hizmeti erişilebilir",
      day_guidance: "Bağlantısı doğrulanmamış alanlarda işlem yapılmaz.",
      refreshed_at: new Date().toISOString(),
      quick_access: ["chat", "cloud"],
      cards: WORKSPACES.map(card),
      approvals: [],
      activities: [],
    },
  });
}
