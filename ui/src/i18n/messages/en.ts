/** English UI strings — landing (phase 1) + panel shell (phase 2). Mirror keys from tr.ts */
import type { MessageTree } from "./tr";
import landing from "./landing/en";
import panel from "./panel/en";
import umbrella from "./umbrella/en";

const en: MessageTree = {
  meta: {
    landingTitle: "Lumos — People First, Technology for the World",
    description:
      "Lumos makes AI, security, and connection flows clearer while preserving human choice and each organisation's identity.",
    ogTitle: "Lumos — People First, Technology for the World",
    ogDescription:
      "An AI control layer designed to stand beside people, serve the world, and help systems work better together.",
    twitterTitle: "Lumos — People First, Technology for the World",
    twitterDescription:
      "An AI control layer designed to stand beside people, serve the world, and help systems work better together.",
  },
  lang: {
    switchLabel: "Language",
    tr: "TR",
    en: "EN",
  },
  nav: {
    aria: "On-page navigation",
    world: "World",
    why: "Why Lumos?",
    modules: "Modules",
    developer: "Developer",
    install: "Setup",
    connect: "Connect",
    panel: "Panel",
    github: "GitHub",
    brandAria: "Lumos — top of page",
    brandTitle: "Lumos",
    brandSub: "WE LOCK AI",
  },
  hero: {
    eyebrow: "WE LOCK AI · LUMOS",
    title: "People first. Technology for the world.",
    subtitle: "A safer way to work better together",
    lead1:
      "Lumos brings people, organisations, and the services they use into clearer, more accessible, and safer flows while preserving their identities.",
    lead2: "It does not replace any person, organisation, or system. It works beside them, makes context visible, and never changes who owns the decision.",
    pillar: "Human dignity · Clear consent · Equal collaboration",
    ctaPanel: "Explore Lumos",
    ctaWorld: "Our world vision",
    askAria: "Ask Lumos — continue in the panel",
    askPlaceholder: "Example: Break a task into safe steps",
    askSubmit: "Open in panel",
    askHint: "No answer here; continue in the panel.",
    askEmpty: "Enter a question to continue.",
  },
  landing,
  panel,
  umbrella,
};

export default en;
