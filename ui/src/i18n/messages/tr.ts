/** Turkish UI strings — landing (phase 1) + panel shell (phase 2). */
import landing from "./landing/tr";
import panel from "./panel/tr";
import umbrella from "./umbrella/tr";

const tr = {
  meta: {
    landingTitle: "We Lock AI — İnsan Merkezli Yapay Zekâ Ekosistemi",
    description:
      "We Lock AI, insan merkezli yapay zekâ ekosistemidir. Lumos; sohbet, görev, dosya ve bağlantıları tek çalışma alanında buluşturan son kullanıcı ürünüdür.",
    ogTitle: "We Lock AI — İnsan Merkezli Yapay Zekâ Ekosistemi",
    ogDescription:
      "We Lock AI, insan merkezli yapay zekâ ekosistemidir. Lumos; sohbet, görev, dosya ve bağlantıları tek çalışma alanında buluşturan son kullanıcı ürünüdür.",
    twitterTitle: "We Lock AI — İnsan Merkezli Yapay Zekâ Ekosistemi",
    twitterDescription:
      "We Lock AI, insan merkezli yapay zekâ ekosistemidir. Lumos; sohbet, görev, dosya ve bağlantıları tek çalışma alanında buluşturan son kullanıcı ürünüdür.",
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
    ecosystem: "Güven",
    panel: "Lumos’u Aç",
    github: "GitHub",
    brandAria: "We Lock AI — sayfa başı",
    brandTitle: "We Lock AI",
    brandSub: "AI EKOSİSTEMİ",
  },
  hero: {
    eyebrow: "WE LOCK AI · LUMOS",
    title: "Lumos",
    subtitle: "Yapay zekâ kontrol katmanı",
    lead1:
      "Lumos yeni bir yapay zekâ değildir. Kullandığınız yapay zekâları (ChatGPT, Copilot ve benzerleri) güvenli, denetlenebilir ve sizin kontrolünüzde çalıştıran ortak katmandır.",
    lead2: "Karar kullanıcıda kalır. Lumos riski, bağlamı ve sonraki adımı görünür kılar.",
    pillar: "Tek panel · Çoklu akış · Kullanıcı kontrolü",
    audience: "Şu an: geliştiriciler için açık kaynak · kurumlar için yol haritada · son kullanıcı paketi yakında.",
    ctaPanel: "Paneli Aç",
    ctaWorld: "Vizyonu oku",
    askAria: "Lumos’a sor — panelde devam eder",
    askPlaceholder: "Örnek: Bir görevi güvenli adımlara böl",
    askSubmit: "Panelde devam et",
    askHint: "Yanıt burada değil; panelde devam eder.",
    askEmpty: "Devam etmek için bir soru yazın.",
  },
  landing,
  panel,
  umbrella,
} as const;

export default tr;
export type MessageTree = typeof tr;
