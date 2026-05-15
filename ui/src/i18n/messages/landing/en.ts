/** Landing page body copy (English) */
import type landingTr from "./tr";

const landingEn: typeof landingTr = {
  principles: {
    title: "Core principles",
    cardUserControlTitle: "User control",
    cardUserControlBody: "The final choice is always yours; Lumos does not replace you.",
    cardRiskTitle: "Risk visibility",
    cardRiskBody: "Possible outcomes and side effects are summarized and shown.",
    cardDataTitle: "Data awareness",
    cardDataBody: "Where data is processed and which limits apply is presented in readable form.",
    cardApprovalTitle: "Explicit approval",
    cardApprovalBody: "Clear, reversible approval flows for permanent or risky steps.",
    workTitle: "How we work",
    workIntro:
      "Lumos under We Lock AI aims to stay consistent across four axes without trading transparency for speed.",
    listUserDecisionLabel: "User decision:",
    listUserDecisionBody: "The final choice is always yours; Lumos does not replace you.",
    listApprovalLabel: "Explicit approval:",
    listApprovalBody: "Clear, reversible approval flows for permanent or risky steps.",
    listRiskLabel: "Risk visibility:",
    listRiskBody: "Possible outcomes and side effects are summarized and shown.",
    listDataLabel: "Data awareness:",
    listDataBody: "Where data is processed and which limits apply is presented in readable form.",
  },
  world: {
    title: "World",
    lead:
      "Lumos aims to adapt interfaces and flows to a wide range of users across language, region, and accessibility. The card beside this text emphasizes connecting the “world” module to a human-scale vision—not a single small icon.",
    linkVision: "World vision",
    linkModules: "Module grid",
    visionCardTitle: "World vision",
    visionCardBody:
      "An intelligent voice, media, and AI network starting from Cyprus; opening to the world with a human-centered control approach.",
  },
  heroScene: {
    holoHeadline: "TO THE FUTURE WITH REASON AND SCIENCE",
    quote: "“The truest guide in life is science and knowledge.”",
    quoteAttribution: "— Atatürk",
  },
  why: {
    title: "Why Lumos?",
    p1: "I designed Lumos with the belief that people must not lose control in the face of technology.",
    p2: "AI is no longer distant. It touches our writing, decisions, apps, and daily work. That is great power—but as it grows, seeing what you approve, where information goes, and how decisions are made matters more.",
    p3: "I see Lumos not as a system that decides for people, but as a helper layer that strengthens the user’s mind, awareness, and will.",
    p4: "Lumos aims to shorten paths, reduce clutter, and make options visible—but the final decision must stay with the user. For hard-to-reverse, permanent, or risky actions, the user should know what is happening, see outcomes, and decide themselves.",
    p5: "Lumos is an actively developed control layer; modules expand gradually. The direction is clear: Lumos stands beside the user, not above them—it works with you, not instead of you.",
    p6: "For me, Lumos is not just software. It is an effort to build a more honest, controlled, and human relationship between people and technology.",
  },
  whatIs: {
    title: "What is Lumos?",
    p1: "Lumos is a control layer that aims to bring voice commands, media workflows, and AI-assisted help into one flow—locally or within security boundaries you define. It bridges apps, files, and external services to break scattered work into more traceable steps.",
    p2: "The goal is to simplify what hides behind complex technical detail; to make where data is processed and what the next step might cause more readable. Lumos is not “autopilot”; it aims to inform the user and pause at critical approval points.",
    p3: "Lumos is actively developed; modules and integrations expand in measured steps—visible roadmap and user approval over promises.",
  },
  whatDoes: {
    title: "What does it do?",
    item1: "Aims to break voice and natural-language tasks into safe, traceable sub-steps.",
    item2: "Organizes media and file flows; aims to increase transparency on share or external transfer.",
    item3: "Presents AI suggestions with context and risk; leaves approval to the user for actions with lasting impact.",
    item4: "Aims to gather identity and service connections under one more manageable layer.",
    item5: "Prioritizes extra warnings and approval flows for high-risk or hard-to-reverse actions.",
  },
  whyNeeded: {
    title: "Why is it needed?",
    p1: "As tools and services multiply, context scatters; users struggle to track what runs where and which permission enables what. Lumos aims to make that visible in one control layer and reduce mistaken approvals and unnecessary data transfer.",
  },
  worldVision: {
    eyebrow: "Global scale",
    title: "World and vision",
    lead: "We aim to make Lumos a consistent, simple, reliable control layer across devices and scenarios. Features will grow in measured, incremental steps; user control and transparency stay central.",
    prose:
      "In practice: we aim for interfaces and flows that respect language, region, and accessibility differences. A consistent framework for localization, keyboard, and voice access is the backbone for Lumos staying human at “world” scale.",
  },
  benefits: {
    title: "What do users gain?",
    item1: "Clearer summary and context for what was done and what comes next.",
    item2: "More transparency on whether data stayed on-device or went to an external service.",
    item3: "A more balanced rhythm between speed and control.",
    item4: "Conscious approval for actions that can have lasting or costly outcomes.",
  },
  developer: {
    title: "Developer access",
    p1: "Lumos is currently in an open-source stage for developer review. End-user install packages are not published yet. Developers can review the source on GitHub and run the project locally.",
    githubBtn: "View on GitHub",
    notice:
      "Lumos is developed as an open, contribution-friendly project. Product identity under We Lock AI, brand assets, official services, API access, and user data remain under a controlled permission model.",
  },
  install: {
    title: "Download and setup",
    intro:
      "Lumos is an actively developed open-source control layer. Developers who want to try it locally can clone from GitHub and run it in their own environment.",
    step1: "Step 1 — Clone the repository",
    step2: "Step 2 — Enter the project folder",
    step3: "Step 3 — Install UI dependencies",
    step4: "Step 4 — Run locally",
    step5: "Step 5 — Open in the browser",
    copy: "Copy",
    copied: "Copied",
    open: "Open",
    disclaimer:
      "These buttons do not run commands; they only copy to the clipboard. Paste and run commands in Terminal yourself.",
    note: "Commands are for local development. Official services, API access, and user data are protected by a controlled permission model.",
    githubOpen: "Open on GitHub",
    tryPanel: "Try the panel",
    versionsTitle: "Versions",
    ossHeading: "Open-source development build:",
    ossBody:
      "Lumos source can be reviewed, run, and contributed to locally by developers. This build is for local development and experimentation.",
    officialHeading: "Official / professional release:",
    officialBody:
      "The official Lumos release under We Lock AI will run with panel, service connections, secure API access, integrations, and user permission flows under control. Download, access, and terms will be announced when ready.",
    footnote:
      "Paid or official service access is managed separately from open-source code—via authentication, user approval, and defined usage limits.",
    officialNotify: "Official release notification",
    soon: "Coming soon",
  },
  modules: {
    title: "Lumos modules",
    deck: "The headings below summarize product scope; detailed module notes continue on this page.",
    detailTitle: "Module descriptions",
    backToTop: "Back to top",
    chatTitle: "Chat",
    chatScope: "Brings text-based tasks into a dialogue surface managed with transparent steps.",
    chatDetail:
      "Brings text-based tasks into a dialogue surface managed with transparent steps. Aims to make source context and uncertainty visible in summaries and suggestions; prioritizes checklists and human approval over automatic execution.",
    visionTitle: "Visual analysis",
    visionScope: "Presents image and screen context in readable summaries; leaves final interpretation to you.",
    visionDetail:
      "Presents image and screen context in readable summaries; leaves final interpretation to you. Aims to keep pause and approval points visible for risky or misleading inferences.",
    voiceTitle: "Voice",
    voiceScope: "Handles voice commands and replies in a controlled flow; permissions and limits stay visible.",
    voiceDetail:
      "Handles voice commands and replies in a controlled flow; permissions and limits stay visible. Aims to clarify local processing vs. transfer to external services.",
    mediaTitle: "Media",
    mediaScope: "Keeps audio, image, and file movement traceable from one panel.",
    mediaDetail:
      "Organizes audio, image, and file transfers; aims to distinguish on-device processing from outbound content. Offers a traceable sequence for convert, merge, or share steps.",
    tasksTitle: "Tasks",
    tasksScope: "Turns scattered work into a visible order across modules.",
    tasksDetail:
      "Turns scattered work into a visible order across modules. Aims to make it easier to track which step lives in which module.",
    mailTitle: "Mail",
    mailScope: "Highlights context and risk in messaging and account interactions.",
    mailDetail:
      "Highlights context and risk in messaging and account interactions. Aims to prioritize clear approval flows for permanent or export-like steps.",
    filesTitle: "Files",
    filesScope: "Clarifies data paths in local and remote file flows.",
    filesDetail:
      "Clarifies data paths in local and remote file flows. Aims to offer extra warnings and summaries for hard-to-reverse share, convert, or delete actions.",
    identityTitle: "Identity",
    identityScope: "Presents session, role, and device trust under one manageable layer.",
    identityDetail:
      "Aims to review sessions, roles, and device trust in one place. Gives clear feedback on profile and permission changes; helps understand where identity data is used.",
    securityTitle: "Security",
    securityScope: "Adds verification and auditability for high-risk actions.",
    securityDetail:
      "Aims to add verification and logging for hard-to-reverse actions like delete, payment, publishing, or account changes. Warns the user on suspicious or repeated requests.",
    integrationTitle: "Integration",
    integrationScope: "Unifies external services in the same control layer; scope stays contractual.",
    integrationDetail:
      "Aims to offer one orchestration surface across third-party APIs, cloud services, and local apps. Scope, duration, and data sharing should stay as contractual and visible as possible per connection.",
  },
  may19: {
    heading: "With respect on 19 May",
    p1: "Publishing this text close to a meaningful day like 19 May holds special value for me.",
    p2: "I remember Gazi Mustafa Kemal Atatürk with respect and celebrate 19 May Commemoration of Atatürk, Youth and Sports Day.",
    p3: "I see the ideals of 19 May—young people, science, independent thought, and the future—not only within one country’s borders but as a reminder valuable for humanity.",
    p4: "I also see Lumos, in that spirit, as a small sincere gift to the young people who will build the future and to everyone who wants to use technology for human good.",
    openBtn: "Begin the moment of respect",
    overlayText: "With respect for science, reason, peace, and human dignity.",
    closeBtn: "Close",
    corner: {
      regionAria: "19 May commemoration",
      line: "Happy 19 May — Commemoration of Atatürk, Youth and Sports Day.",
      sub: "We remember Atatürk with respect and gratitude.",
      minimizeAria: "Minimize",
      fabAria: "Open 19 May commemoration",
    },
  },
  assets: {
    /** Until a neutral or EN-only graphic ships, paths may match TR; swap when assets land in `public/`. */
    worldMapDecor: "/lumos-world-map.jpg",
    heroAtaScene: "/lumos-world-map.jpg",
    ogImage: "https://welockai.com/lumos-world-map.jpg",
  },
};

export default landingEn;
