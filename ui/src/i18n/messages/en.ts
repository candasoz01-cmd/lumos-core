/** English UI strings — landing (phase 1) + panel shell (phase 2). Mirror keys from tr.ts */
import type { MessageTree } from "./tr";
import landing from "./landing/en";
import panel from "./panel/en";
import umbrella from "./umbrella/en";

const en: MessageTree = {
  meta: {
    landingTitle: "Lumos — AI Control Layer",
    description:
      "Lumos is a prototype AI control layer that unifies voice, media, tasks, files, and multi-panel flows in one place.",
    ogTitle: "Lumos — AI Control Layer",
    ogDescription:
      "Lumos is a prototype AI control layer that unifies voice, media, tasks, files, and multi-panel flows in one place.",
    twitterTitle: "Lumos — AI Control Layer",
    twitterDescription:
      "Lumos is a prototype AI control layer that unifies voice, media, tasks, files, and multi-panel flows in one place.",
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
    title: "Lumos",
    subtitle: "AI control layer",
    lead1:
      "An intelligent assistant layer that unifies voice, media, visual analysis, tasks, files, identity, and security flows in one panel.",
    lead2: "The decision stays with you. Lumos makes risk, context, and next steps visible.",
    pillar: "One panel · Multiple flows · User control",
    ctaPanel: "Open Lumos Panel",
    ctaWorld: "Read the vision",
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
