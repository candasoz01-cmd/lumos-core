# Mobile Phase 0 — PWA shell

This phase adds a **minimal Progressive Web App (PWA) shell** for the Lumos UI (Astro + Vite in `ui/`). It is intentionally narrow: installable metadata and mobile theme tags only.

## In scope

- `ui/public/manifest.webmanifest` — app name, standalone display, dark/cyan theme colors
- HTML `<head>` metadata on landing (`/`) and panel (`/panel`) — manifest link, `theme-color`, mobile web app tags
- Existing public icon assets referenced in the manifest (no new binary icons)

## Out of scope (not yet)

- Android / iOS native projects
- Capacitor, React Native, or other native wrappers
- Service worker or offline caching
- Native permissions: camera, notifications, filesystem, etc.
- Changes to bridge, chat, or runtime behavior

## Theme reference

Colors match the current dark panel palette:

| Field | Value | Source |
|-------|-------|--------|
| `theme_color` | `#38CEFF` | `--lumos-land-teal` (56 206 255) |
| `background_color` | `#030714` | `--lumos-bg` / `--lumos-main-bg` |

## Verify locally

```bash
cd ui
npm run build
npm run preview
```

In DevTools → Application → Manifest, confirm the manifest loads and icons resolve.

## Next phases (future)

- Service worker / offline strategy (explicit design + approval)
- Native mobile shells or permission flows (separate phase)
