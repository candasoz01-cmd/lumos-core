/** Turkish UI strings — landing (phase 1) + panel shell (phase 2). */
import landing from "./landing/tr";
import panel from "./panel/tr";
import umbrella from "./umbrella/tr";

const tr = {
  meta: {
    landingTitle: "Lumos — Önce İnsan, Dünya İçin Teknoloji",
    description:
      "Lumos, insanın kararını ve kurumların kimliğini koruyarak yapay zekâ, güvenlik ve bağlantı akışlarını daha anlaşılır hâle getirir.",
    ogTitle: "Lumos — Önce İnsan, Dünya İçin Teknoloji",
    ogDescription:
      "İnsanın yanında duran, dünyaya hizmet etmeyi ve birlikte daha iyi çalışmayı amaçlayan yapay zekâ kontrol katmanı.",
    twitterTitle: "Lumos — Önce İnsan, Dünya İçin Teknoloji",
    twitterDescription:
      "İnsanın yanında duran, dünyaya hizmet etmeyi ve birlikte daha iyi çalışmayı amaçlayan yapay zekâ kontrol katmanı.",
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
    connect: "Bağlan",
    panel: "Panel",
    github: "GitHub",
    brandAria: "Lumos — sayfa başı",
    brandTitle: "Lumos",
    brandSub: "WE LOCK AI",
  },
  hero: {
    eyebrow: "WE LOCK AI · LUMOS",
    title: "Önce insan. Dünya için teknoloji.",
    subtitle: "Birlikte daha güzel çalışmanın güvenli yolu",
    lead1:
      "Lumos; insanları, kurumları ve kullandıkları hizmetleri kendi kimliklerini koruyarak daha anlaşılır, erişilebilir ve güvenli akışlarda buluşturur.",
    lead2: "Hiçbir insanın, kurumun veya sistemin yerine geçmez. Yanında çalışır; bağlamı görünür kılar, kararın sahibini değiştirmez.",
    pillar: "İnsan onuru · Açık onay · Eşit iş birliği",
    ctaPanel: "Lumos’u keşfet",
    ctaWorld: "Dünya vizyonumuz",
    askAria: "Lumos’a sor — geliştirici panelinde devam eder",
    askPlaceholder: "Örnek: Bir görevi güvenli adımlara böl",
    askSubmit: "Panelde devam et",
    askHint: "Yanıt burada değil; geliştirici panelinde devam eder.",
    askEmpty: "Devam etmek için bir soru yazın.",
  },
  landing,
  panel,
  umbrella,
} as const;

export default tr;
export type MessageTree = typeof tr;
