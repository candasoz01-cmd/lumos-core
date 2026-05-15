/** English UI strings — landing (phase 1). Mirror keys from tr.ts */
import type { MessageTree } from "./tr";
import landing from "./landing/en";

const en: MessageTree = {
  meta: {
    landingTitle: "Lumos by We Lock AI",
    description:
      "Lumos under We Lock AI: an AI control and assistant layer that unifies multiple flows in one panel while keeping decisions with you.",
    ogTitle: "Lumos by We Lock AI",
    ogDescription: "Lumos is a human-centered AI control layer developed under We Lock AI.",
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
    ctaWorld: "Explore the world",
    askAria: "Ask Lumos",
    askPlaceholder: "Ask Lumos: “Break a task into safe steps…”",
    askSubmit: "Ask",
  },
  landing,
};

export default en;
