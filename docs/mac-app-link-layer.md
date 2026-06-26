# Mac app — production link layer

Minimal URLs and Universal Links prep for a future Lumos Mac client. No native app in this repo.

## Production URLs (open in browser or hand off to Mac app)

| Purpose | URL |
|---------|-----|
| Landing | `https://welockai.com/` |
| Panel | `https://welockai.com/panel` |
| PWA manifest | `https://welockai.com/manifest.webmanifest` |

Bridge/chat proxy (same origin as panel): `https://welockai.com/api/bridge/*` (serverless proxy; upstream configured on Vercel).

## Universal Links (Apple)

Served at:

- `https://welockai.com/.well-known/apple-app-site-association`
- `https://welockai.com/apple-app-site-association` (legacy path)

**TODO before shipping a signed Mac/iOS app:** replace `XXXXXXXXXX` in `appID` with your [Apple Team ID](https://developer.apple.com/help/account/manage-your-team/locate-your-team-id/) and confirm the bundle identifier (`com.welockai.lumos` placeholder) matches the app target.

Associated domains entitlement example: `applinks:welockai.com`
