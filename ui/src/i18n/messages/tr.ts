/** Turkish UI strings — landing (phase 1). Panel keys live in ./panel/ for phase 2. */
import landing from "./landing/tr";

const tr = {
  meta: {
    landingTitle: "Lumos — Yapay Zekâ Kontrol Katmanı",
    description:
      "Lumos; ses, medya, görevler, dosyalar ve çoklu panel akışlarını tek yerde birleştiren yapay zekâ kontrol katmanı prototipidir.",
    ogTitle: "Lumos — Yapay Zekâ Kontrol Katmanı",
    ogDescription:
      "Lumos; ses, medya, görevler, dosyalar ve çoklu panel akışlarını tek yerde birleştiren yapay zekâ kontrol katmanı prototipidir.",
    twitterTitle: "Lumos — Yapay Zekâ Kontrol Katmanı",
    twitterDescription:
      "Lumos; ses, medya, görevler, dosyalar ve çoklu panel akışlarını tek yerde birleştiren yapay zekâ kontrol katmanı prototipidir.",
  },
  lang: {
    switchLabel: "Dil seçimi",
    tr: "TR",
    en: "EN",
  },
  nav: {
    aria: "Sayfa içi gezinme",
    world: "Dünya",
    why: "Neden Lumos?",
    modules: "Modüller",
    developer: "Geliştirici",
    install: "Kurulum",
    panel: "Panel",
    github: "GitHub",
    brandAria: "Lumos — sayfa başı",
    brandTitle: "Lumos",
    brandSub: "WE LOCK AI",
  },
  hero: {
    eyebrow: "WE LOCK AI · LUMOS",
    title: "Lumos",
    subtitle: "Yapay zekâ kontrol katmanı",
    lead1:
      "Ses, medya, görsel analiz, görevler, dosyalar, kimlik ve güvenlik akışlarını tek panelde birleştiren akıllı asistan altyapısı.",
    lead2: "Karar kullanıcıda kalır. Lumos riski, bağlamı ve sonraki adımı görünür kılar.",
    pillar: "Tek panel · Çoklu akış · Kullanıcı kontrolü",
    ctaPanel: "Lumos Panel’e Git",
    ctaWorld: "Dünyayı Keşfet",
    askAria: "Lumos’a sor",
    askPlaceholder: "Lumos’a sor: “Bir görevi güvenli adımlara ayır…”",
    askSubmit: "Sor",
  },
  landing,
} as const;

export default tr;
export type MessageTree = typeof tr;
