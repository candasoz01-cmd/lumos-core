/** Turkish UI strings — landing (phase 1) + panel shell (phase 2). */
import landing from "./landing/tr";
import panel from "./panel/tr";
import umbrella from "./umbrella/tr";

const tr = {
  meta: {
    landingTitle: "Lumos — kontrol katmanı",
    description:
      "Lumos yeni bir yapay zekâ değildir. Kendi modelini çalıştırmaz. Barındırılan sohbet, anahtar varsa iletiyi bir model API’sine gönderir ve bu iletiyi Lumos veritabanına yazmaz.",
    ogTitle: "Lumos — kontrol katmanı",
    ogDescription:
      "Lumos yeni bir yapay zekâ değildir. Kendi modelini çalıştırmaz. Barındırılan sohbet, anahtar varsa iletiyi bir model API’sine gönderir ve bu iletiyi Lumos veritabanına yazmaz.",
    twitterTitle: "Lumos — kontrol katmanı",
    twitterDescription:
      "Lumos yeni bir yapay zekâ değildir. Kendi modelini çalıştırmaz. Barındırılan sohbet, anahtar varsa iletiyi bir model API’sine gönderir ve bu iletiyi Lumos veritabanına yazmaz.",
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
    subtitle: "Kontrol katmanı",
    lead1:
      "Lumos yeni bir yapay zekâ değildir. Kendi modelini çalıştırmaz. Anahtar tanımlıysa iletiniz bir model API’sine gider.",
    lead2:
      "Barındırılan sohbet bu iletiyi Lumos veritabanına yazmaz. Yanıtta sağlayıcı ve model adı yoktur.",
    lead3:
      "Onay katmanı, ortam değişkeni açık değilse çalışmaz. Sohbet yanıtı ayrı bir onay adımı beklemez.",
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
