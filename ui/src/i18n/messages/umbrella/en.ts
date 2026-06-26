/** WeLockAI umbrella — product surfaces (EN) */
import type umbrellaTr from "./tr";

const umbrellaEn: typeof umbrellaTr = {
  nav: {
    aria: "We Lock AI site",
    home: "Home",
    connect: "Connect",
    slack: "Slack",
    mac: "Mac",
    cyber: "Cyber",
    panel: "Panel",
    github: "GitHub",
  },
  products: {
    title: "Connect",
    lead:
      "Lumos surfaces under We Lock AI in one place: web panel, Slack integration, Mac app links, and the security-focused Cyber variant.",
    panelTitle: "Lumos Panel",
    panelBody: "Primary web workspace for tasks, chat, files, and approval flows.",
    panelCta: "Open panel",
    slackTitle: "Lumos in Slack",
    slackBody: "Workplace context, channel summaries, mentions, and controlled notifications (coming soon).",
    slackCta: "Slack page",
    macTitle: "Mac / Apple",
    macBody: "Universal Links and the future Lumos Mac client link layer.",
    macCta: "Mac links",
    cyberTitle: "Lumos Cyber",
    cyberBody: "Security and risk-visibility variant — early access planned.",
    cyberCta: "Cyber page",
  },
  footer: {
    tagline: "We Lock AI · welockai.com — Lumos product family",
    rights: "Open-source core on GitHub; official services use controlled access.",
  },
  slack: {
    metaTitle: "Lumos in Slack — We Lock AI",
    metaDescription:
      "Lumos as a Slack workspace companion: work context, controlled notifications, and approval — no OAuth started here.",
    eyebrow: "WE LOCK AI · SLACK",
    title: "Lumos in Slack",
    lead:
      "Slack is one of Lumos’s primary workplace surfaces. Channel summaries, mention/thread context, and controlled notifications are planned; full workspace archive or unapproved posting is not the goal.",
    whatTitle: "What it offers",
    what1: "Policy-scoped channel and thread context aligned with the Lumos panel.",
    what2: "Explicit approval and grant model for external actions (posting, channel admin).",
    what3: "Workplace notification surface kept separate from mail channels.",
    statusTitle: "Status",
    statusBody:
      "Slack OAuth and setup wizard are not on this site yet. Integration principles are documented in the open-source repo; this page will update when connection is available.",
    panelCta: "Go to web panel",
    homeCta: "Home",
  },
  mac: {
    metaTitle: "Lumos Mac — Universal Links — We Lock AI",
    metaDescription:
      "Universal Links on welockai.com for the future Lumos Mac client, panel URLs, and Apple App Site Association.",
    eyebrow: "WE LOCK AI · MAC",
    title: "Mac and Apple links",
    lead:
      "The future Lumos Mac client can open panel and landing URLs on welockai.com. OAuth and Apple Sign In are not started on this page.",
    urlsTitle: "Production URLs",
    ulTitle: "Universal Links (AASA)",
    ulBody:
      "Apple App Site Association is served at the paths below. Update Team ID and bundle ID before shipping a signed Mac app.",
    ulPaths: "Supported paths: /, /panel, /panel/*",
    bundleNote: "Placeholder bundle: com.welockai.lumos — Team ID still marked XXXXXXXXXX.",
    panelCta: "Open panel",
    homeCta: "Home",
  },
  cyber: {
    metaTitle: "Lumos Cyber — We Lock AI",
    metaDescription:
      "Lumos Cyber: security, risk visibility, and controlled approval under We Lock AI — early access.",
    eyebrow: "WE LOCK AI · CYBER",
    title: "Lumos Cyber",
    lead:
      "Lumos Cyber is the planned We Lock AI variant for security operations, risk visibility, and policy-focused work. It is not a cyberpunk UI — it is a professional control layer.",
    focusTitle: "Focus",
    focus1: "Keeping risk and policy summaries visible in the panel.",
    focus2: "Extra approval and audit trail for high-impact steps.",
    focus3: "Enterprise policy aligned with the We Lock AI private layer (in production).",
    statusTitle: "Status",
    statusBody:
      "Dedicated Cyber landing and feature set are not complete yet. For now the Lumos panel and open-source core are the base surfaces; this page provides visibility under the brand umbrella.",
    panelCta: "Lumos panel",
    homeCta: "Home",
  },
};

export default umbrellaEn;
