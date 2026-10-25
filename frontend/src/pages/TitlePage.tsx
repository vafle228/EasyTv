import { useCallback, useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { api } from "../api";
import { Icon } from "../components/Icons";
import { Notice } from "../components/Notice";
import { PosterArt } from "../components/Poster";
import { useLoad } from "../hooks";
import { R } from "../routes";
import { Link } from "../router";
import type { SavedTitle, Variant } from "../types";
import { PickDialog } from "./PickDialog";
import type { StreamTarget } from "./PickDialog";
import { PLAYER_LABEL, VoiceDialog, plural } from "./VoiceDialog";

const PAGE = 100;

/** Prefer the dub the user picked before; otherwise the first one with a direct MP4 player. */
function chooseDub(variants: Variant[], preferred: string | null): Variant | undefined {
  return (
    variants.find((v) => v.translationId === preferred) ??
    variants.find((v) => v.providers.some((p) => p !== "aniboom")) ??
    variants[0]
  );
}

/** A title on animego: card, dub and player choice, episodes; watch in the browser or on a TV, save, download. */
export function TitlePage({ titleId }: { titleId: string }) {
  const title = useLoad(() => api.title(titleId), titleId);
  const eps = useLoad(() => api.episodes(titleId), titleId);
  const [saved, setSaved] = useState<SavedTitle | null>(null);
  const [episode, setEpisode] = useState<number | null>(null);
  const [variants, setVariants] = useState<Variant[] | null>(null);
  const [variantsError, setVariantsError] = useState<string | null>(null);
  const [dubId, setDubId] = useState<string | null>(null);
  const [provider, setProvider] = useState("auto");
  const [page, setPage] = useState(0);
  const [jump, setJump] = useState("");
  const [voiceOpen, setVoiceOpen] = useState(false);
  const [pick, setPick] = useState<StreamTarget | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const cache = useRef(new Map<number, Variant[]>());

  const t = title.data;
  const list = eps.data;
  const movie = list !== null && list.length === 0;

  useEffect(() => setSaved(t?.saved ?? null), [t]);

  // Where to start: the episode the user stopped at, else the first one; 0 means a movie.
  useEffect(() => {
    if (list === null || t === null || episode !== null) return;
    const start = list.length === 0 ? 0 : (t.saved?.lastEpisode ?? list[0].number);
    setEpisode(start);
    setDubId(t.saved?.translationId ?? null);
    const idx = list.findIndex((e) => e.number === start);
    setPage(idx > 0 ? Math.floor(idx / PAGE) : 0);
  }, [list, t, episode]);

  const variantsOf = useCallback(
    async (n: number) => {
      const hit = cache.current.get(n);
      if (hit) return hit;
      const vs = await api.variants(titleId, n);
      cache.current.set(n, vs);
      return vs;
    },
    [titleId],
  );

  useEffect(() => {
    if (episode === null) return;
    let alive = true;
    setVariants(null);
    setVariantsError(null);
    variantsOf(episode)
      .then((vs) => {
        if (!alive) return;
        setVariants(vs);
        setDubId((cur) => chooseDub(vs, cur)?.translationId ?? null);
      })
      .catch((e) => alive && setVariantsError(e instanceof Error ? e.message : String(e)));
    return () => {
      alive = false;
    };
  }, [episode, variantsOf]);

  const dub = variants?.find((v) => v.translationId === dubId);
  const playerOk = provider === "auto" || !!dub?.providers.includes(provider);

  const target = (n: number, d: Variant): StreamTarget => ({
    ref: { titleId, episode: n, translationId: d.translationId, provider: playerOk ? provider : "auto" },
    title: t ? (n > 0 ? `${t.title}, ${n} серия` : t.title) : `${n} серия`,
    translation: d.translation,
  });

  /** Picks the episode, settles its dub (they differ between episodes) and runs `then` with the target. */
  const withEpisode = async (n: number, then: (s: StreamTarget) => void | Promise<void>) => {
    setError(null);
    try {
      const vs = await variantsOf(n);
      const d = chooseDub(vs, dubId);
      if (!d) throw new Error(`У ${n} серии пока нет видео на animego`);
      if (n !== episode) setEpisode(n);
      if (d.translationId !== dubId) {
        if (dub) setInfo(`У ${n} серии нет озвучки ${dub.translation}, взял ${d.translation}.`);
        setDubId(d.translationId);
      }
      await then(target(n, d));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const watch = (n: number) => withEpisode(n, (s) => setPick(s));

  const download = (n: number) =>
    withEpisode(n, async (s) => {
      setBusy(`dl-${n}`);
      try {
        await api.downloadEpisode(s.ref, s.translation ? `${s.title} (${s.translation})` : s.title);
        setInfo(`${s.title}: скачиваю в библиотеку. Прогресс виден в «Загрузках», потом серию можно показать без интернета.`);
      } finally {
        setBusy(null);
      }
    });

  const toggleSaved = async () => {
    setBusy("save");
    setError(null);
    try {
      if (saved) {
        await api.unsaveTitle(titleId);
        setSaved(null);
      } else {
        setSaved(await api.saveTitle(titleId));
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(null);
    }
  };

  const onJump = (e: FormEvent) => {
    e.preventDefault();
    const n = Number(jump);
    const idx = list?.findIndex((x) => x.number === n) ?? -1;
    if (idx < 0) {
      setError(`Серии ${jump} нет на animego`);
      return;
    }
    setPage(Math.floor(idx / PAGE));
    setEpisode(n);
    setJump("");
  };

  if (title.error && !t) {
    return (
      <main className="page">
        <BackLink />
        <Notice title="Не открылась карточка на animego" text={title.error} onClose={() => void title.reload()} />
      </main>
    );
  }

  const watched = new Set(saved?.watched ?? []);
  const pages = list ? Math.ceil(list.length / PAGE) : 0;
  const shown = list?.slice(page * PAGE, (page + 1) * PAGE) ?? [];
  const current = episode ?? 0;

  return (
    <main className="page">
      <BackLink />

      <section className="card">
        <div className="hero">
          <div className="poster">
            <PosterArt id={titleId} title={t?.title ?? ""} src={t?.poster ?? null} />
          </div>
          <div>
            <p className="label">
              <Icon name="globe" /> animego
            </p>
            <h1 className="hero__title">{t?.title ?? "Загружаю…"}</h1>
            {t && (
              <p className="hero__orig">
                {[t.originalTitle, t.year, t.kind === "movie" ? "Фильм" : "Сериал"].filter(Boolean).join(", ")}
              </p>
            )}
            {t && t.genres.length > 0 && (
              <div className="chips">
                {t.genres.map((g) => (
                  <span key={g} className="chip chip--static">
                    {g}
                  </span>
                ))}
              </div>
            )}
            {t?.description && <p className="hero__text">{t.description}</p>}
            {t && (
              <dl className="facts facts--wide" style={{ maxWidth: 640, marginTop: 20 }}>
                <dt>Серий</dt>
                <dd>{movie ? "фильм" : list ? `${list.length}${t.episodesTotal ? ` из ${t.episodesTotal}` : ""}` : "…"}</dd>
                <dt>Озвучки</dt>
                <dd>{variants ? `${variants.length} у этой серии` : "…"}</dd>
                {t.studio && (
                  <>
                    <dt>Студия</dt>
                    <dd>{t.studio}</dd>
                  </>
                )}
                {t.rating != null && (
                  <>
                    <dt>Рейтинг</dt>
                    <dd>★ {t.rating}</dd>
                  </>
                )}
                <dt>У вас</dt>
                <dd>{saved ? (watched.size ? `в кинотеатре, начато ${watched.size}` : "в кинотеатре") : "не сохранено"}</dd>
              </dl>
            )}
            <div className="hero__actions">
              <button
                className="btn btn--primary"
                disabled={!dub || episode === null}
                onClick={() => watch(current)}
              >
                <Icon name="play" />
                {movie ? "Смотреть фильм" : episode !== null ? `Смотреть ${episode} серию` : "Смотреть"}
              </button>
              <button className="btn" onClick={toggleSaved} disabled={!t || busy === "save"}>
                <Icon name={saved ? "check" : "bookmark"} />
                {saved ? "В кинотеатре" : "Сохранить в кинотеатр"}
              </button>
              {t?.url && (
                <a className="link" href={t.url} target="_blank" rel="noreferrer">
                  Открыть на animego
                </a>
              )}
            </div>
            <p className="small muted" style={{ marginTop: 12 }}>
              «Смотреть» пускает видео через этот сервер без скачивания: в браузере или на телевизоре. Ссылки с сайта
              живут недолго, поэтому сервер получает свежую прямо перед просмотром.
            </p>
          </div>
        </div>
      </section>

      {error && <Notice title="Не получилось" text={error} onClose={() => setError(null)} />}
      {info && <Notice tone="info" title="Готово" text={info} onClose={() => setInfo(null)} />}

      <section className="card">
        <h2 className="label">Озвучка и плеер{movie ? "" : episode ? `, ${episode} серия` : ""}</h2>
        {variantsError && <p className="video__error">{variantsError}</p>}
        <div className="optgrid">
          <span className="optline">Озвучка</span>
          <button className="select" onClick={() => setVoiceOpen(true)} disabled={!variants?.length}>
            <span className="select__v">{dub?.translation ?? (variants ? "нет видео" : "загружаю…")}</span>
            {variants && variants.length > 1 && <span className="tag">ещё {variants.length - 1}</span>}
            <Icon name="chevron" />
          </button>
          <span className="small muted hint">
            Выбор запомнится, если тайтл в кинотеатре. Если у другой серии такой озвучки нет, возьму первую с готовым
            MP4.
          </span>
          <span className="optline">Плеер</span>
          <div className="segmented" role="radiogroup" aria-label="Плеер">
            <button className="segmented__item" role="radio" aria-checked={provider === "auto"} onClick={() => setProvider("auto")}>
              Авто
            </button>
            {(dub?.providers ?? []).map((p) => (
              <button key={p} className="segmented__item" role="radio" aria-checked={provider === p} onClick={() => setProvider(p)}>
                {PLAYER_LABEL[p] ?? p}
              </button>
            ))}
          </div>
          <span className="small muted hint">
            Авто: CVH, потом Kodik. Они отдают готовый MP4. Aniboom отдаёт только HLS, его без ffmpeg пока не показать.
          </span>
        </div>
      </section>

      {!movie && (
        <section className="card">
          <div className="section-head">
            <h2 className="label">Серии на сайте</h2>
            <span className="small muted">
              {list ? `${list.length} ${plural(list.length, "серия", "серии", "серий")}` : "Загружаю…"}
              {dub ? `, озвучка ${dub.translation}` : ""}
            </span>
          </div>
          {eps.error && <p className="video__error">{eps.error}</p>}
          {list && list.length > 0 && (
            <div className="eptools">
              {pages > 1 ? (
                <div className="segmented scroller" role="radiogroup" aria-label="Диапазон серий">
                  {Array.from({ length: pages }, (_, i) => {
                    const chunk = list.slice(i * PAGE, (i + 1) * PAGE);
                    return (
                      <button key={i} className="segmented__item" role="radio" aria-checked={page === i} onClick={() => setPage(i)}>
                        {chunk[0].number}–{chunk[chunk.length - 1].number}
                      </button>
                    );
                  })}
                </div>
              ) : (
                <span />
              )}
              <form className="jump" onSubmit={onJump}>
                <label className="field">
                  <Icon name="search" />
                  <input
                    type="text"
                    inputMode="numeric"
                    placeholder="Серия №"
                    aria-label="Перейти к серии"
                    value={jump}
                    onChange={(e) => setJump(e.target.value.replace(/\D/g, ""))}
                  />
                </label>
              </form>
            </div>
          )}
          <ul className="eps">
            {shown.map((e) => {
              const seen = watched.has(e.number);
              const selected = e.number === episode;
              return (
                <li key={e.number} className={`video ep ${seen ? "ep--watched" : ""} ${selected ? "video--selected" : ""}`}>
                  <button
                    className="ep__num"
                    style={{ border: 0, cursor: "pointer", background: "transparent" }}
                    onClick={() => setEpisode(e.number)}
                    aria-label={`Выбрать ${e.number} серию`}
                  >
                    {seen ? <Icon name="check" /> : e.number}
                  </button>
                  <div className="video__main">
                    <span className="video__title">{e.title ? `${e.number}. ${e.title}` : `${e.number} серия`}</span>
                    <span className="video__meta">
                      {[e.date, seen ? "начинали смотреть" : null, saved?.lastEpisode === e.number ? "остановились здесь" : null]
                        .filter(Boolean)
                        .join(", ") || "На сайте"}
                    </span>
                  </div>
                  <div className="video__actions">
                    <button className={`btn btn--small ${selected ? "btn--primary" : ""}`} onClick={() => watch(e.number)}>
                      <Icon name="play" />
                      Смотреть
                    </button>
                    <button
                      className="icon-btn icon-btn--neutral"
                      aria-label={`Скачать ${e.number} серию`}
                      title="Скачать в библиотеку"
                      disabled={busy === `dl-${e.number}`}
                      onClick={() => download(e.number)}
                    >
                      <Icon name="download" />
                    </button>
                  </div>
                </li>
              );
            })}
          </ul>
        </section>
      )}

      {movie && dub && (
        <section className="card">
          <div className="row row--between">
            <span className="muted">Фильм можно скачать в библиотеку и смотреть без интернета.</span>
            <button className="btn" onClick={() => download(0)} disabled={busy === "dl-0"}>
              <Icon name="download" />
              Скачать фильм
            </button>
          </div>
        </section>
      )}

      {voiceOpen && variants && (
        <VoiceDialog
          title={t?.title ?? ""}
          episode={current}
          variants={variants}
          current={dubId}
          onClose={() => setVoiceOpen(false)}
          onPick={(v) => {
            setDubId(v.translationId);
            if (provider !== "auto" && !v.providers.includes(provider)) setProvider("auto");
            setVoiceOpen(false);
          }}
        />
      )}
      {pick && <PickDialog videoId={null} stream={pick} onClose={() => setPick(null)} />}
    </main>
  );
}

function BackLink() {
  return (
    <Link className="btn btn--small back" to={R.catalog} onClick={(e) => {
      if (window.history.length > 1) {
        e.preventDefault();
        window.history.back();
      }
    }}>
      <Icon name="back" />
      Каталог animego
    </Link>
  );
}
