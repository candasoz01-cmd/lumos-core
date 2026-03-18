/**
 * Kando post kartı: yalnızca içerik + puan satırı.
 * Etiket yok, emoji yok, algoritma açıklaması yok.
 * API: content, ratingAvg (null olabilir), ratingCount, createdAt (ISO string)
 */

export function formatRelativeTime(iso) {
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return "—";
  const sec = Math.max(0, Math.floor((Date.now() - t) / 1000));
  if (sec < 60) return "Az önce";
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min} dakika önce`;
  const h = Math.floor(min / 60);
  if (h < 24) return `${h} saat önce`;
  const d = Math.floor(h / 24);
  if (d < 30) return `${d} gün önce`;
  const mo = Math.floor(d / 30);
  if (mo < 12) return `${mo} ay önce`;
  return `${Math.floor(d / 365)} yıl önce`;
}

export function formatPostMeta({ ratingAvg, ratingCount, createdAt }) {
  const n = Number(ratingCount) || 0;
  const avg =
    ratingAvg != null && ratingAvg !== ""
      ? Number(ratingAvg).toFixed(1)
      : null;
  const left = avg != null ? `${avg} (${n} oy)` : `— (${n} oy)`;
  return `${left} \u2022 ${formatRelativeTime(createdAt)}`;
}

function isWithinLastHours(iso, hours) {
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return false;
  return Date.now() - t < hours * 60 * 60 * 1000;
}

/** Puan rakamı: >=4 hafif belirgin, <=2.5 hafif soluk. */
function ratingFigureClass(ratingAvg) {
  if (ratingAvg == null || ratingAvg === "") return "text-zinc-400";
  const v = Number(ratingAvg);
  if (Number.isNaN(v)) return "text-zinc-400";
  if (v >= 4) return "text-zinc-50";
  if (v <= 2.5) return "text-zinc-700";
  return "text-zinc-400";
}

export default function KandoPostCard({ content, ratingAvg, ratingCount, createdAt }) {
  const text = content != null ? String(content) : "";
  const n = Number(ratingCount) || 0;
  const avg =
    ratingAvg != null && ratingAvg !== ""
      ? Number(ratingAvg).toFixed(1)
      : null;
  const fresh = isWithinLastHours(createdAt, 2);
  const bgClass = fresh ? "bg-zinc-900/[0.14]" : "bg-zinc-950/70";

  return (
    <article className={`rounded-2xl border border-zinc-800 ${bgClass} p-4`}>
      <div className="text-zinc-100 text-base font-medium leading-snug break-words">{text}</div>
      <div className="mt-2 text-sm tabular-nums text-zinc-500">
        <span className={ratingFigureClass(ratingAvg)}>{avg ?? "—"}</span>
        {` (${n} oy) \u2022 ${formatRelativeTime(createdAt)}`}
      </div>
    </article>
  );
}
