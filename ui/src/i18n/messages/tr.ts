/** Turkish UI strings — landing (phase 1) + panel shell (phase 2). */
import landing from "./landing/tr";
import panel from "./panel/tr";
import umbrella from "./umbrella/tr";

const tr = {
  meta: {
    landingTitle: "Lumos — kontrol katmanı",
    description:
      "Lumos yeni bir yapay zekâ değildir. Kendi modelini çalıştırmaz. Barındırılan sohbet, anahtar varsa iletiyi ve oturumdaki adı bir model API’sine gönderir; sohbet işleyicisi iletiyi kendi içinde veritabanına yazmaz, “hatırla” denirse özet ayrı hafıza servisine yazılır.",
    ogTitle: "Lumos — kontrol katmanı",
    ogDescription:
      "Lumos yeni bir yapay zekâ değildir. Kendi modelini çalıştırmaz. Barındırılan sohbet, anahtar varsa iletiyi ve oturumdaki adı bir model API’sine gönderir; sohbet işleyicisi iletiyi kendi içinde veritabanına yazmaz, “hatırla” denirse özet ayrı hafıza servisine yazılır.",
    twitterTitle: "Lumos — kontrol katmanı",
    twitterDescription:
      "Lumos yeni bir yapay zekâ değildir. Kendi modelini çalıştırmaz. Barındırılan sohbet, anahtar varsa iletiyi ve oturumdaki adı bir model API’sine gönderir; sohbet işleyicisi iletiyi kendi içinde veritabanına yazmaz, “hatırla” denirse özet ayrı hafıza servisine yazılır.",
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
    brandAria: "Lumos AI — sayfa başı",
    brandTitle: "Lumos AI",
    brandSub: "AI EKOSİSTEMİ",
  },
  hero: {
    eyebrow: "WE LOCK AI · LUMOS",
    title: "Lumos",
    subtitle: "Sen söyle, Lumos hazırlasın. Son karar senin.",
    lead1:
      "Lumos yeni bir yapay zekâ değildir. Kendi modelini çalıştırmaz. Anahtar tanımlıysa iletiniz bir model API’sine gider.",
    lead2:
      "Sohbet işleyicisi iletiyi kendi içinde veritabanına yazmaz; “hatırla” denirse özet ayrı hafıza servisine yazılır. Yanıtta sağlayıcı ve model adı yoktur.",
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
