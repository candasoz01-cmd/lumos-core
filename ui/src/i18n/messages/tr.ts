/** Turkish UI strings — landing (phase 1). Panel keys live in ./panel/ for phase 2. */
import landing from "./landing/tr";

const tr = {
  meta: {
    landingTitle: "Lumos by We Lock AI",
    description:
      "We Lock AI çatısı altındaki Lumos: tek panelde çoklu akışı bir araya getiren, kararı kullanıcıda tutan yapay zekâ kontrol ve asistan katmanı.",
    ogTitle: "Lumos by We Lock AI",
    ogDescription:
      "Lumos, We Lock AI çatısı altında geliştirilen insan merkezli yapay zekâ kontrol katmanıdır.",
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
