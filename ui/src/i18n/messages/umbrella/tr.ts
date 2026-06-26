/** WeLockAI umbrella — product surfaces (TR) */
const umbrellaTr = {
  nav: {
    aria: "We Lock AI site",
    home: "Ana sayfa",
    connect: "Bağlan",
    slack: "Slack",
    mac: "Mac",
    cyber: "Cyber",
    panel: "Panel",
    github: "GitHub",
  },
  products: {
    title: "Bağlan",
    lead:
      "We Lock AI çatısı altındaki Lumos yüzeyleri tek adreste: web paneli, Slack entegrasyonu, Mac uygulaması ve güvenlik odaklı Cyber varyantı.",
    panelTitle: "Lumos Panel",
    panelBody: "Görevler, sohbet, dosyalar ve onay akışları için birincil web çalışma alanı.",
    panelCta: "Paneli aç",
    slackTitle: "Lumos in Slack",
    slackBody: "İş yeri bağlamında kanal özeti, mention ve kontrollü bildirim yüzeyi (yakında).",
    slackCta: "Slack sayfası",
    macTitle: "Mac / Apple",
    macBody: "Universal Links ve gelecekteki Lumos Mac istemcisi için bağlantı katmanı.",
    macCta: "Mac bağlantıları",
    cyberTitle: "Lumos Cyber",
    cyberBody: "Güvenlik ve risk görünürlüğü odaklı varyant — erken erişim planlanıyor.",
    cyberCta: "Cyber sayfası",
  },
  footer: {
    tagline: "We Lock AI · welockai.com — Lumos ürün ailesi",
    rights: "Açık kaynak çekirdek GitHub'da; resmi servisler kontrollü erişimle.",
  },
  slack: {
    metaTitle: "Lumos in Slack — We Lock AI",
    metaDescription:
      "Lumos'un Slack içi çalışma arkadaşı yüzeyi: iş bağlamı, kontrollü bildirim ve onay — OAuth burada başlatılmaz.",
    eyebrow: "WE LOCK AI · SLACK",
    title: "Lumos in Slack",
    lead:
      "Slack, Lumos'un iş yeri bağlamında çalıştığı birincil kanallardan biridir. Kanal özeti, mention/thread bağlamı ve kontrollü bildirimler planlanır; tam workspace arşivi veya onaysız mesaj gönderimi hedeflenmez.",
    whatTitle: "Ne sunar?",
    what1: "Politika kapsamındaki kanal ve thread bağlamını Lumos paneliyle hizalı özetler.",
    what2: "Dış etkili adımlarda (mesaj gönderme, kanal yönetimi) açık onay ve grant modeli.",
    what3: "Mail kanalından ayrı tutulan iş yeri bildirim yüzeyi.",
    statusTitle: "Durum",
    statusBody:
      "Slack OAuth ve kurulum sihirbazı henüz bu sitede yok. Entegrasyon kararı ve izin modeli açık kaynak repoda belgelenmiştir; bağlantı hazır olduğunda bu sayfa güncellenecektir.",
    panelCta: "Web paneline git",
    homeCta: "Ana sayfa",
  },
  mac: {
    metaTitle: "Lumos Mac — Universal Links — We Lock AI",
    metaDescription:
      "Lumos Mac istemcisi için welockai.com Universal Links, panel URL'leri ve Apple App Site Association.",
    eyebrow: "WE LOCK AI · MAC",
    title: "Mac ve Apple bağlantıları",
    lead:
      "Gelecekteki Lumos Mac istemcisi welockai.com üzerinden panel ve landing URL'lerini açabilir. OAuth veya Apple Sign In bu sayfada başlatılmaz.",
    urlsTitle: "Üretim URL'leri",
    ulTitle: "Universal Links (AASA)",
    ulBody:
      "Apple App Site Association dosyası aşağıdaki yollarda sunulur. İmzalı Mac uygulaması yayınlanmadan önce Team ID ve bundle kimliği güncellenmelidir.",
    ulPaths: "Desteklenen yollar: /, /panel, /panel/*",
    bundleNote:
      "Placeholder bundle: com.welockai.lumos — Team ID henüz XXXXXXXXXX olarak işaretli.",
    panelCta: "Paneli aç",
    homeCta: "Ana sayfa",
  },
  cyber: {
    metaTitle: "Lumos Cyber — We Lock AI",
    metaDescription:
      "Lumos Cyber: güvenlik, risk görünürlüğü ve kontrollü onay odaklı We Lock AI varyantı — erken erişim.",
    eyebrow: "WE LOCK AI · CYBER",
    title: "Lumos Cyber",
    lead:
      "Lumos Cyber, We Lock AI çatısı altında güvenlik operasyonları, risk görünürlüğü ve politika odaklı çalışma için planlanan varyanttır. Ayrı bir cyberpunk arayüz değil; profesyonel kontrol katmanıdır.",
    focusTitle: "Odak",
    focus1: "Risk ve politika özetlerinin panelde görünür tutulması.",
    focus2: "Yüksek etkili adımlarda ek onay ve audit izi.",
    focus3: "We Lock AI private katmanıyla hizalı kurumsal politika (üretimde).",
    statusTitle: "Durum",
    statusBody:
      "Cyber özel landing ve özellik seti henüz tamamlanmadı. Şimdilik Lumos paneli ve açık kaynak çekirdek temel yüzeydir; bu sayfa marka çatısı altında görünürlük sağlar.",
    panelCta: "Lumos paneli",
    homeCta: "Ana sayfa",
  },
} as const;

export default umbrellaTr;
