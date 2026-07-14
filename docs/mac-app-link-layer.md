# Mac app — production link layer

Minimal URLs and Universal Links prep for a future Lumos Mac client. No native app in this repo.

## Production URLs (open in browser or hand off to Mac app)

| Purpose | URL |
|---------|-----|
| Landing | `https://welockai.com/` |
| Panel | `https://welockai.com/panel` |
| Slack (info) | `https://welockai.com/slack` |
| Mac / Universal Links | `https://welockai.com/connect/mac` |
| Lumos Cyber (info) | `https://welockai.com/cyber` |
| PWA manifest | `https://welockai.com/manifest.webmanifest` |

Bridge/chat proxy (same origin as panel): `https://welockai.com/api/bridge/*` (serverless proxy; upstream configured on Vercel).

## Universal Links (Apple)

Served at:

- `https://welockai.com/.well-known/apple-app-site-association`
- `https://welockai.com/apple-app-site-association` (legacy path)

The signed app contract is configured as Team ID `VQH79C5QU7` with bundle identifier `com.welockai.Lumos`. The app target must include the associated domain `applinks:welockai.com`.

Associated domains entitlement example: `applinks:welockai.com`
