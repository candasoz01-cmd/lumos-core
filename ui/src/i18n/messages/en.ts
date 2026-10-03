/** English UI strings — landing (phase 1) + panel shell (phase 2). Mirror keys from tr.ts */
import type { MessageTree } from "./tr";
import landing from "./landing/en";
import panel from "./panel/en";
import umbrella from "./umbrella/en";

const en: MessageTree = {
  meta: {
    landingTitle: "Lumos — control layer",
    description:
      "Lumos is not a new artificial intelligence. It does not run its own model. Hosted chat sends the message and the signed-in name to a model API when a key is set; the chat handler itself does not write it to a database, and a “remember” summary goes to the separate memory service.",
    ogTitle: "Lumos — control layer",
    ogDescription:
      "Lumos is not a new artificial intelligence. It does not run its own model. Hosted chat sends the message and the signed-in name to a model API when a key is set; the chat handler itself does not write it to a database, and a “remember” summary goes to the separate memory service.",
    twitterTitle: "Lumos — control layer",
    twitterDescription:
      "Lumos is not a new artificial intelligence. It does not run its own model. Hosted chat sends the message and the signed-in name to a model API when a key is set; the chat handler itself does not write it to a database, and a “remember” summary goes to the separate memory service.",
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
    ecosystem: "Trust",
    panel: "Open Lumos",
    github: "GitHub",
    brandAria: "We Lock AI — top of page",
    brandTitle: "We Lock AI",
    brandSub: "AI ECOSYSTEM",
  },
  hero: {
    eyebrow: "WE LOCK AI · LUMOS",
    title: "Lumos",
    subtitle: "Control layer",
    lead1:
      "Lumos is not a new artificial intelligence. It does not run its own model. When a key is set, your message goes to a model API.",
    lead2:
      "The chat handler itself does not write the message to a database; a “remember” summary goes to the separate memory service. The response does not include a provider or model name.",
    lead3:
      "The confirmation layer does not run unless its environment flag is on. A chat reply is not held for a separate approval step.",
    pillar: "One panel · Multiple flows · User control",
    audience: "Right now: open source for developers · on the roadmap for organizations · end-user package coming soon.",
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
