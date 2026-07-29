export type IntegrationGuideCategory =
  | "development"
  | "productivity"
  | "communication"
  | "social"
  | "browser"
  | "ai"
  | "device";

export type IntegrationGuideStatus =
  | "foundation"
  | "limited"
  | "planned"
  | "connectionCheck"
  | "configurationRequired"
  | "catalog"
  | "localDiscovery";

export type IntegrationGuideSource = "global_catalog" | "specialized_surface" | "catalog_aggregate";

export interface IntegrationGuideItem {
  id: string;
  catalogId: string | readonly string[];
  source: IntegrationGuideSource;
  name: string;
  category: IntegrationGuideCategory;
  status: IntegrationGuideStatus;
  regions: readonly string[];
}

/**
 * Public guide projection of GLOBAL_INTEGRATION_CATALOG.
 *
 * `catalogId` values mirror the provider ids in
 * `src/integrations/providers/global_catalog_provider.py`. Existing Gmail,
 * Google Calendar and Google Drive surfaces remain explicit specialized
 * exceptions because they are not entries in that representative catalog.
 *
 * A guide item never means connected. Statuses describe only the strongest
 * evidence that can be shown publicly without changing provider behavior.
 */
export const INTEGRATION_GUIDE_ITEMS = [
  {
    id: "github",
    catalogId: "github",
    source: "global_catalog",
    name: "GitHub",
    category: "development",
    status: "foundation",
    regions: ["Global"],
  },
  {
    id: "jira",
    catalogId: "jira",
    source: "global_catalog",
    name: "Jira",
    category: "development",
    status: "catalog",
    regions: ["Global"],
  },
  {
    id: "linear",
    catalogId: "linear",
    source: "global_catalog",
    name: "Linear",
    category: "development",
    status: "catalog",
    regions: ["Global"],
  },
  {
    id: "gmail",
    catalogId: "mail",
    source: "specialized_surface",
    name: "Gmail",
    category: "productivity",
    status: "limited",
    regions: ["Global"],
  },
  {
    id: "googleCalendar",
    catalogId: "google_calendar",
    source: "specialized_surface",
    name: "Google Calendar",
    category: "productivity",
    status: "planned",
    regions: ["Global"],
  },
  {
    id: "googleDrive",
    catalogId: "google_drive",
    source: "specialized_surface",
    name: "Google Drive",
    category: "productivity",
    status: "planned",
    regions: ["Global"],
  },
  {
    id: "notion",
    catalogId: "notion",
    source: "global_catalog",
    name: "Notion",
    category: "productivity",
    status: "catalog",
    regions: ["Global"],
  },
  {
    id: "slack",
    catalogId: "slack",
    source: "global_catalog",
    name: "Slack",
    category: "communication",
    status: "catalog",
    regions: ["Global"],
  },
  {
    id: "whatsapp",
    catalogId: "whatsapp",
    source: "global_catalog",
    name: "WhatsApp",
    category: "communication",
    status: "connectionCheck",
    regions: ["Global", "IN"],
  },
  {
    id: "telegram",
    catalogId: "telegram",
    source: "global_catalog",
    name: "Telegram",
    category: "communication",
    status: "connectionCheck",
    regions: ["Global", "IN", "RU"],
  },
  {
    id: "zoom",
    catalogId: "zoom",
    source: "global_catalog",
    name: "Zoom",
    category: "communication",
    status: "catalog",
    regions: ["Global"],
  },
  {
    id: "microsoftTeams",
    catalogId: "microsoft_teams",
    source: "global_catalog",
    name: "Microsoft Teams",
    category: "communication",
    status: "catalog",
    regions: ["Global"],
  },
  {
    id: "line",
    catalogId: "line",
    source: "global_catalog",
    name: "LINE",
    category: "communication",
    status: "catalog",
    regions: ["JP", "TW", "TH"],
  },
  {
    id: "kakaoTalk",
    catalogId: "kakao_talk",
    source: "global_catalog",
    name: "KakaoTalk",
    category: "communication",
    status: "catalog",
    regions: ["KR"],
  },
  {
    id: "wechat",
    catalogId: "wechat",
    source: "global_catalog",
    name: "WeChat",
    category: "communication",
    status: "configurationRequired",
    regions: ["CN", "Global"],
  },
  {
    id: "lark",
    catalogId: "lark",
    source: "global_catalog",
    name: "Lark / Feishu",
    category: "communication",
    status: "configurationRequired",
    regions: ["CN", "APAC", "Global"],
  },
  {
    id: "dingtalk",
    catalogId: "dingtalk",
    source: "global_catalog",
    name: "DingTalk",
    category: "communication",
    status: "configurationRequired",
    regions: ["CN"],
  },
  {
    id: "naverWorks",
    catalogId: "naver_works",
    source: "global_catalog",
    name: "NAVER WORKS",
    category: "communication",
    status: "catalog",
    regions: ["KR", "JP"],
  },
  {
    id: "jioMeet",
    catalogId: "jiomeet",
    source: "global_catalog",
    name: "JioMeet",
    category: "communication",
    status: "catalog",
    regions: ["IN"],
  },
  {
    id: "vk",
    catalogId: "vk",
    source: "global_catalog",
    name: "VK",
    category: "social",
    status: "catalog",
    regions: ["RU", "CIS"],
  },
  {
    id: "chrome",
    catalogId: "google_chrome",
    source: "global_catalog",
    name: "Google Chrome",
    category: "browser",
    status: "catalog",
    regions: ["Global"],
  },
  {
    id: "safari",
    catalogId: "apple_safari",
    source: "global_catalog",
    name: "Safari",
    category: "browser",
    status: "catalog",
    regions: ["Global"],
  },
  {
    id: "yandexBrowser",
    catalogId: "yandex_browser",
    source: "global_catalog",
    name: "Yandex Browser",
    category: "browser",
    status: "catalog",
    regions: ["RU", "CIS"],
  },
  {
    id: "openai",
    catalogId: "openai",
    source: "global_catalog",
    name: "OpenAI",
    category: "ai",
    status: "foundation",
    regions: ["Global"],
  },
  {
    id: "gemini",
    catalogId: "google_gemini",
    source: "global_catalog",
    name: "Gemini",
    category: "ai",
    status: "catalog",
    regions: ["Global"],
  },
  {
    id: "deepseek",
    catalogId: "deepseek",
    source: "global_catalog",
    name: "DeepSeek",
    category: "ai",
    status: "catalog",
    regions: ["CN", "Global"],
  },
  {
    id: "qwen",
    catalogId: "qwen",
    source: "global_catalog",
    name: "Qwen",
    category: "ai",
    status: "catalog",
    regions: ["CN", "Global"],
  },
  {
    id: "yandexGpt",
    catalogId: "yandex_gpt",
    source: "global_catalog",
    name: "YandexGPT",
    category: "ai",
    status: "catalog",
    regions: ["RU", "CIS"],
  },
  {
    id: "hyperClova",
    catalogId: "naver_hyperclova",
    source: "global_catalog",
    name: "HyperCLOVA X",
    category: "ai",
    status: "catalog",
    regions: ["KR"],
  },
  {
    id: "bluetoothAudio",
    catalogId: ["bluetooth_classic_audio", "bluetooth_le_audio"],
    source: "catalog_aggregate",
    name: "Bluetooth Audio",
    category: "device",
    status: "localDiscovery",
    regions: ["Global"],
  },
  {
    id: "matter",
    catalogId: "matter",
    source: "global_catalog",
    name: "Matter",
    category: "device",
    status: "catalog",
    regions: ["Global"],
  },
  {
    id: "homeAssistant",
    catalogId: "home_assistant",
    source: "global_catalog",
    name: "Home Assistant",
    category: "device",
    status: "catalog",
    regions: ["Global"],
  },
  {
    id: "smartThings",
    catalogId: "samsung_smartthings",
    source: "global_catalog",
    name: "SmartThings",
    category: "device",
    status: "catalog",
    regions: ["KR", "Global"],
  },
  {
    id: "sonos",
    catalogId: "sonos",
    source: "global_catalog",
    name: "Sonos",
    category: "device",
    status: "catalog",
    regions: ["Global"],
  },
] as const satisfies readonly IntegrationGuideItem[];

export const INTEGRATION_GUIDE_CATEGORY_ORDER = [
  "development",
  "productivity",
  "communication",
  "social",
  "browser",
  "ai",
  "device",
] as const satisfies readonly IntegrationGuideCategory[];

export const INTEGRATION_GUIDE_GROUPS = INTEGRATION_GUIDE_CATEGORY_ORDER.map((category) => ({
  category,
  items: INTEGRATION_GUIDE_ITEMS.filter((item) => item.category === category),
}));
