import { useEffect, useState } from "react";
import { Icon } from "../components/Icons";
import type { Variant } from "../types";

export const PLAYER_LABEL: Record<string, string> = { cvh: "CVH 1080p", kodik: "Kodik 720p", aniboom: "Aniboom, HLS" };

/** «Озвучка»: the dubs of the chosen episode with the players that carry each one. */
export function VoiceDialog({
  title,
  episode,
  variants,
  current,
  onPick,
  onClose,
}: {
  title: string;
  episode: number;
  variants: Variant[];
  current: string | null;
  onPick: (v: Variant) => void;
  onClose: () => void;
}) {
  const [choice, setChoice] = useState(current ?? variants[0]?.translationId ?? null);
  const [query, setQuery] = useState("");

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const q = query.trim().toLowerCase();
  const shown = variants.filter((v) => !q || v.translation.toLowerCase().includes(q));
  const picked = variants.find((v) => v.translationId === choice);

  return (
    <div className="scrim scrim--overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <section className="card dialog dialog--wide" role="dialog" aria-modal="true" aria-labelledby="voice-title">
        <div className="row row--between" style={{ alignItems: "flex-start", flexWrap: "nowrap" }}>
          <div className="grow">
            <p className="label">Озвучка</p>
            <h1 id="voice-title" className="title">
              {title}
            </h1>
            <p className="small muted">
              {variants.length} {plural(variants.length, "вариант", "варианта", "вариантов")} на animego
              {episode > 0 ? ` у ${episode} серии` : ""}. Выбор запомнится для этого тайтла.
            </p>
          </div>
          <button className="icon-btn icon-btn--flat icon-btn--neutral" onClick={onClose} aria-label="Закрыть">
            <Icon name="close" />
          </button>
        </div>
        {variants.length > 6 && (
          <div className="row" style={{ margin: "18px 0 0" }}>
            <label className="field" style={{ minHeight: 48 }}>
              <Icon name="search" />
              <input
                type="text"
                placeholder="Найти студию"
                aria-label="Найти студию"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </label>
          </div>
        )}
        <ul className="opts opts--list" role="radiogroup" aria-label="Озвучка" style={{ marginTop: 18 }}>
          {shown.map((v) => (
            <li key={v.translationId}>
              <button
                className="opt"
                role="radio"
                aria-checked={v.translationId === choice}
                onClick={() => setChoice(v.translationId)}
                onDoubleClick={() => onPick(v)}
              >
                <span className="opt__radio" />
                <span className="opt__main">
                  <span className="opt__name">{v.translation || "Без названия"}</span>
                  <span className="opt__meta">
                    {v.providers.some((p) => p !== "aniboom")
                      ? "Готовый MP4: играет и в браузере, и на телевизоре"
                      : "Только HLS: без ffmpeg пока не показать"}
                  </span>
                </span>
                <span className="opt__players">
                  {v.providers.map((p) => (
                    <span key={p} className="tag">
                      {PLAYER_LABEL[p] ?? p}
                    </span>
                  ))}
                </span>
              </button>
            </li>
          ))}
          {shown.length === 0 && <li className="muted small">Такой студии нет у этой серии.</li>}
        </ul>
        <div className="dialog__foot">
          <span className="small muted">CVH и Kodik отдают готовый MP4, его можно показать на любом телевизоре.</span>
          <div className="row">
            <button className="btn btn--small" onClick={onClose}>
              Отмена
            </button>
            <button className="btn btn--primary btn--small" disabled={!picked} onClick={() => picked && onPick(picked)}>
              <Icon name="check" />
              {picked ? `Выбрать ${picked.translation}` : "Выбрать"}
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}

export function plural(n: number, one: string, few: string, many: string): string {
  const m10 = n % 10;
  const m100 = n % 100;
  if (m10 === 1 && m100 !== 11) return one;
  if (m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14)) return few;
  return many;
}
