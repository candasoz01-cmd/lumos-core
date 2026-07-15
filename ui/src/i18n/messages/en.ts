/** English UI strings — landing (phase 1) + panel shell (phase 2). Mirror keys from tr.ts */
import type { MessageTree } from "./tr";
import landing from "./landing/en";
import panel from "./panel/en";
import umbrella from "./umbrella/en";

const en: MessageTree = {
  meta: {
    landingTitle: "We Lock AI — Human-Centered AI Ecosystem",
    description:
      "We Lock AI is a human-centered AI ecosystem. Lumos is its end-user product for chat, tasks, files, and connected work in one place.",
    ogTitle: "We Lock AI — Human-Centered AI Ecosystem",
    ogDescription:
      "We Lock AI is a human-centered AI ecosystem. Lumos is its end-user product for chat, tasks, files, and connected work in one place.",
    twitterTitle: "We Lock AI — Human-Centered AI Ecosystem",
    twitterDescription:
      "We Lock AI is a human-centered AI ecosystem. Lumos is its end-user product for chat, tasks, files, and connected work in one place.",
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
    panel: "Open Lumos",
    github: "GitHub",
    brandAria: "We Lock AI — top of page",
    brandTitle: "We Lock AI",
    brandSub: "AI ECOSYSTEM",
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
