from __future__ import annotations

from typing import Any

from integrations.models import IntegrationRequest, IntegrationResult


def _entry(
    provider_id: str,
    name: str,
    category: str,
    regions: tuple[str, ...],
    connection_kind: str,
    support_level: str = "discovery_only",
    capabilities: tuple[str, ...] = (),
) -> dict[str, Any]:
    return {
        "provider_id": provider_id,
        "name": name,
        "category": category,
        "regions": regions,
        "connection_kind": connection_kind,
        "support_level": support_level,
        "capabilities": capabilities,
    }


GLOBAL_INTEGRATION_CATALOG: tuple[dict[str, Any], ...] = (
    # Messaging and regional communication
    _entry("whatsapp", "WhatsApp", "messaging", ("global",), "cloud_api", "connection_check", ("messages", "webhooks")),
    _entry("telegram", "Telegram", "messaging", ("global",), "bot_api", "connection_check", ("messages", "bots", "webhooks")),
    _entry("signal", "Signal", "messaging", ("global",), "local_bridge", capabilities=("messages",)),
    _entry("line", "LINE", "messaging", ("JP", "TW", "TH"), "oauth_webhook", capabilities=("messages", "official_account")),
    _entry("kakao_talk", "KakaoTalk", "messaging", ("KR",), "oauth_api", capabilities=("messages", "social_login")),
    _entry("wechat", "WeChat", "messaging", ("CN", "global"), "official_account_api", capabilities=("messages", "mini_programs")),
    _entry("viber", "Viber", "messaging", ("EE", "ME", "SEA", "global"), "bot_api", capabilities=("messages", "bots")),
    _entry("zalo", "Zalo", "messaging", ("VN",), "official_account_api", capabilities=("messages", "official_account")),
    _entry("naver_works", "NAVER WORKS", "messaging", ("KR", "JP"), "oauth_api", capabilities=("messages", "calendar", "contacts")),
    _entry("wecom", "WeCom", "messaging", ("CN",), "enterprise_api", capabilities=("messages", "contacts", "calendar")),

    # Meetings and calls
    _entry("zoom", "Zoom", "meeting", ("global",), "oauth_webhook", capabilities=("meetings", "recordings", "webhooks")),
    _entry("microsoft_teams", "Microsoft Teams", "meeting", ("global",), "oauth_graph_api", capabilities=("meetings", "messages", "calendar")),
    _entry("google_meet", "Google Meet", "meeting", ("global",), "oauth_api", capabilities=("meetings", "calendar")),
    _entry("webex", "Cisco Webex", "meeting", ("global",), "oauth_webhook", capabilities=("meetings", "messages")),
    _entry("jitsi", "Jitsi Meet", "meeting", ("global",), "self_hosted_api", capabilities=("meetings",)),
    _entry("tencent_meeting", "Tencent Meeting / VooV", "meeting", ("CN", "APAC"), "oauth_api", capabilities=("meetings", "webhooks")),
    _entry("lark_meetings", "Lark / Feishu Meetings", "meeting", ("CN", "APAC", "global"), "app_api", capabilities=("meetings", "calendar")),
    _entry("jiomeet", "JioMeet", "meeting", ("IN",), "partner_api", capabilities=("meetings",)),

    # Browsers and browser surfaces
    _entry("google_chrome", "Google Chrome", "browser", ("global",), "browser_extension", capabilities=("tabs", "page_context", "automation")),
    _entry("apple_safari", "Apple Safari", "browser", ("global",), "browser_extension", capabilities=("tabs", "page_context")),
    _entry("microsoft_edge", "Microsoft Edge", "browser", ("global",), "browser_extension", capabilities=("tabs", "page_context", "automation")),
    _entry("mozilla_firefox", "Mozilla Firefox", "browser", ("global",), "browser_extension", capabilities=("tabs", "page_context", "automation")),
    _entry("brave", "Brave", "browser", ("global",), "chromium_extension", capabilities=("tabs", "page_context")),
    _entry("opera", "Opera", "browser", ("global",), "chromium_extension", capabilities=("tabs", "page_context")),
    _entry("samsung_internet", "Samsung Internet", "browser", ("KR", "global"), "android_extension", capabilities=("page_context",)),
    _entry("yandex_browser", "Yandex Browser", "browser", ("RU", "CIS"), "chromium_extension", capabilities=("tabs", "page_context")),
    _entry("uc_browser", "UC Browser", "browser", ("CN", "IN", "SEA", "AF"), "mobile_bridge", capabilities=("page_context",)),
    _entry("qq_browser", "QQ Browser", "browser", ("CN",), "mobile_bridge", capabilities=("page_context",)),
    _entry("360_browser", "360 Secure Browser", "browser", ("CN",), "chromium_extension", capabilities=("tabs", "page_context")),

    # Social media
    _entry("facebook", "Facebook", "social", ("global",), "oauth_graph_api", capabilities=("pages", "posts", "messages")),
    _entry("instagram", "Instagram", "social", ("global",), "oauth_graph_api", capabilities=("media", "comments", "messages")),
    _entry("x", "X", "social", ("global",), "oauth_api", capabilities=("posts", "mentions")),
    _entry("linkedin", "LinkedIn", "social", ("global",), "oauth_api", capabilities=("profile", "pages", "posts")),
    _entry("threads", "Threads", "social", ("global",), "oauth_api", capabilities=("posts", "replies")),
    _entry("tiktok", "TikTok", "social", ("global",), "oauth_api", capabilities=("video", "profile")),
    _entry("weibo", "Weibo", "social", ("CN",), "oauth_api", capabilities=("posts", "profile")),
    _entry("douyin", "Douyin", "social", ("CN",), "oauth_api", capabilities=("video", "profile")),
    _entry("vk", "VK", "social", ("RU", "CIS"), "oauth_api", capabilities=("posts", "messages", "communities")),
    _entry("naver_band", "NAVER BAND", "social", ("KR", "JP"), "oauth_api", capabilities=("groups", "posts")),
    _entry("kakao_story", "KakaoStory", "social", ("KR",), "oauth_api", capabilities=("posts", "profile")),
    _entry("mixi", "mixi", "social", ("JP",), "partner_api", capabilities=("communities", "profile")),
    _entry("sharechat", "ShareChat", "social", ("IN",), "partner_api", capabilities=("posts", "video")),

    # AI providers and platforms
    _entry("openai", "OpenAI", "ai", ("global",), "api_key", "registered", ("chat", "tools", "vision")),
    _entry("anthropic", "Anthropic", "ai", ("global",), "api_key", capabilities=("chat", "tools", "vision")),
    _entry("google_gemini", "Google Gemini", "ai", ("global",), "api_key_oauth", capabilities=("chat", "tools", "multimodal")),
    _entry("microsoft_copilot", "Microsoft Copilot", "ai", ("global",), "oauth_api", capabilities=("chat", "enterprise_data")),
    _entry("perplexity", "Perplexity", "ai", ("global",), "api_key", capabilities=("search", "chat")),
    _entry("mistral", "Mistral AI", "ai", ("EU", "global"), "api_key", capabilities=("chat", "tools")),
    _entry("deepseek", "DeepSeek", "ai", ("CN", "global"), "api_key", capabilities=("chat", "reasoning")),
    _entry("qwen", "Qwen", "ai", ("CN", "global"), "api_key", capabilities=("chat", "multimodal")),
    _entry("baidu_ernie", "Baidu ERNIE", "ai", ("CN",), "api_key", capabilities=("chat", "multimodal")),
    _entry("naver_hyperclova", "HyperCLOVA X", "ai", ("KR",), "api_key", capabilities=("chat", "korean_language")),
    _entry("yandex_gpt", "YandexGPT", "ai", ("RU", "CIS"), "api_key", capabilities=("chat", "russian_language")),
    _entry("groq", "GroqCloud", "ai", ("global",), "api_key", capabilities=("inference", "chat")),

    # Work and developer tools
    _entry("slack", "Slack", "work_tool", ("global",), "oauth_webhook", capabilities=("messages", "channels", "files")),
    _entry("notion", "Notion", "work_tool", ("global",), "oauth_api", capabilities=("pages", "databases")),
    _entry("asana", "Asana", "work_tool", ("global",), "oauth_webhook", capabilities=("tasks", "projects")),
    _entry("linear", "Linear", "work_tool", ("global",), "oauth_webhook", capabilities=("issues", "projects")),
    _entry("jira", "Jira", "work_tool", ("global",), "oauth_webhook", capabilities=("issues", "projects")),
    _entry("trello", "Trello", "work_tool", ("global",), "oauth_webhook", capabilities=("boards", "cards")),
    _entry("clickup", "ClickUp", "work_tool", ("global",), "oauth_webhook", capabilities=("tasks", "docs")),
    _entry("monday", "monday.com", "work_tool", ("global",), "oauth_api", capabilities=("boards", "items")),
    _entry("github", "GitHub", "work_tool", ("global",), "app_oauth", capabilities=("repositories", "issues", "pull_requests")),
    _entry("gitlab", "GitLab", "work_tool", ("global",), "oauth_webhook", capabilities=("repositories", "issues", "merge_requests")),
    _entry("bitbucket", "Bitbucket", "work_tool", ("global",), "oauth_webhook", capabilities=("repositories", "pull_requests")),
    _entry("kintone", "Cybozu kintone", "work_tool", ("JP", "APAC"), "api_token_oauth", capabilities=("apps", "records", "workflows")),
    _entry("chatwork", "Chatwork", "work_tool", ("JP",), "oauth_api", capabilities=("messages", "tasks", "rooms")),
    _entry("lark", "Lark / Feishu", "work_tool", ("CN", "APAC", "global"), "app_api", "registered", ("messages", "docs", "calendar")),
    _entry("dingtalk", "DingTalk", "work_tool", ("CN",), "app_api", "registered", ("messages", "docs", "calendar")),
    _entry("zoho_workplace", "Zoho Workplace", "work_tool", ("IN", "global"), "oauth_api", capabilities=("mail", "docs", "calendar")),

    # Device protocols and ecosystems. Discovery does not imply control permission.
    _entry("bluetooth_classic_audio", "Bluetooth Classic Audio", "device", ("global",), "os_bluetooth_bridge", capabilities=("a2dp", "hfp", "avrcp", "audio_output", "microphone")),
    _entry("bluetooth_le_audio", "Bluetooth LE Audio / Auracast", "device", ("global",), "os_bluetooth_bridge", capabilities=("le_audio", "auracast", "audio_output", "microphone")),
    _entry("bluetooth_hid", "Bluetooth HID", "device", ("global",), "os_bluetooth_bridge", capabilities=("keyboard", "mouse", "controller")),
    _entry("matter", "Matter", "device", ("global",), "local_protocol", capabilities=("discovery", "state", "control")),
    _entry("apple_home", "Apple Home", "device", ("global",), "os_framework", capabilities=("home_devices", "scenes")),
    _entry("google_home", "Google Home", "device", ("global",), "oauth_cloud_api", capabilities=("home_devices", "automations")),
    _entry("amazon_alexa", "Amazon Alexa", "device", ("global",), "skill_api", capabilities=("home_devices", "voice")),
    _entry("samsung_smartthings", "Samsung SmartThings", "device", ("KR", "global"), "oauth_cloud_api", capabilities=("home_devices", "automations")),
    _entry("xiaomi_home", "Xiaomi Home", "device", ("CN", "global"), "vendor_cloud_api", capabilities=("home_devices",)),
    _entry("huawei_ai_life", "Huawei AI Life", "device", ("CN", "global"), "vendor_sdk", capabilities=("audio", "network", "home_devices")),
    _entry("tuya_smart_life", "Tuya / Smart Life", "device", ("CN", "global"), "oauth_cloud_api", capabilities=("home_devices", "automations")),
    _entry("home_assistant", "Home Assistant", "device", ("global",), "local_api", capabilities=("discovery", "state", "automations")),
    _entry("sonos", "Sonos", "device", ("global",), "oauth_cloud_api", capabilities=("audio_output", "groups", "playback")),
    _entry("bose", "Bose", "device", ("global",), "vendor_sdk", capabilities=("audio_output", "headphones")),
    _entry("sony_audio", "Sony Audio", "device", ("JP", "global"), "vendor_sdk", capabilities=("audio_output", "headphones")),
    _entry("jbl", "JBL", "device", ("global",), "vendor_sdk", capabilities=("audio_output", "speakers", "headphones")),
    _entry("yamaha_musiccast", "Yamaha MusicCast", "device", ("JP", "global"), "local_api", capabilities=("audio_output", "zones", "playback")),
    _entry("denon_heos", "Denon HEOS", "device", ("JP", "global"), "local_api", capabilities=("audio_output", "zones", "playback")),
    _entry("lg_thinq", "LG ThinQ", "device", ("KR", "global"), "oauth_cloud_api", capabilities=("home_devices", "appliances")),
)

CATALOG_BY_ID = {entry["provider_id"]: entry for entry in GLOBAL_INTEGRATION_CATALOG}


def _public_entry(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        **entry,
        "regions": list(entry["regions"]),
        "capabilities": list(entry["capabilities"]),
        "connected": False,
    }


def _matches(entry: dict[str, Any], category: str, region: str, capability: str) -> bool:
    if category and entry["category"] != category:
        return False
    if region and region not in entry["regions"] and "global" not in entry["regions"]:
        return False
    if capability and capability not in entry["capabilities"]:
        return False
    return True


def run_global_catalog_action(request: IntegrationRequest) -> IntegrationResult:
    action = request.action.strip().lower()
    if action == "list_catalog":
        category = str(request.payload.get("category", "")).strip().lower()
        region = str(request.payload.get("region", request.region)).strip().upper()
        capability = str(request.payload.get("capability", "")).strip().lower()
        providers = [
            _public_entry(entry)
            for entry in GLOBAL_INTEGRATION_CATALOG
            if _matches(entry, category, region, capability)
        ]
        return IntegrationResult(
            True,
            request.provider,
            request.action,
            {
                "count": len(providers),
                "providers": providers,
                "filters": {"category": category, "region": region, "capability": capability},
                "catalog_scope": "representative_extensible",
                "connection_claim": "metadata_only",
            },
        )

    if action == "provider_details":
        provider_id = str(request.payload.get("provider_id", "")).strip().lower()
        entry = CATALOG_BY_ID.get(provider_id)
        if entry is None:
            return IntegrationResult(False, request.provider, request.action, {"provider_id": provider_id}, "global_provider_unknown")
        return IntegrationResult(True, request.provider, request.action, _public_entry(entry))

    return IntegrationResult(False, request.provider, request.action, {}, "unsupported_global_catalog_action")


def register_global_catalog_provider(register) -> None:
    register("global_catalog", "list_catalog", run_global_catalog_action)
    register("global_catalog", "provider_details", run_global_catalog_action)
