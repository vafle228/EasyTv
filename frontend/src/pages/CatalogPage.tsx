import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { api } from "../api";
import { Icon } from "../components/Icons";
import { Notice } from "../components/Notice";
import { PosterArt } from "../components/Poster";
import { R } from "../routes";
import { Link } from "../router";
import type { CatalogTitle } from "../types";

const EXAMPLES = ["Фрирен", "Магическая битва", "Наруто", "Дандадан", "Монолог фармацевта"];

const queryFromUrl = () => new URLSearchParams(window.location.search).get("q") ?? "";

/** Catalogs: search animego, open a title, keep it in the cinema. */
export function CatalogPage() {
  const [query, setQuery] = useState(queryFromUrl);
  const [searched, setSearched] = useState<string | null>(null);
  const [results, setResults] = useState<CatalogTitle[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState<string | null>(null);

  const search = async (q: string) => {
    q = q.trim();
    if (!q) return;
    window.history.replaceState(null, "", R.catalogSearch(q));
    setBusy(true);
    setError(null);
    try {
      setResults(await api.search(q));
      setSearched(q);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    const q = queryFromUrl();
    if (q) void search(q);
  }, []);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    void search(query);
  };

  const toggleSaved = async (t: CatalogTitle) => {
    setSaving(t.id);
    setError(null);
    try {
      if (t.saved) await api.unsaveTitle(t.id);
      else await api.saveTitle(t.id);
      setResults((rs) => rs?.map((r) => (r.id === t.id ? { ...r, saved: !t.saved } : r)) ?? null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(null);
    }
  };

  return (
    <main className="page">
      <section className="card">
        <div className="card__head" style={{ marginBottom: 22 }}>
          <div>
            <h1 className="label">Каталоги</h1>
            <p className="muted">
              Найдите аниме на animego и смотрите серии в браузере или на телевизоре. Понравившееся сохраните в
              кинотеатр: там запомнится, где вы остановились.
            </p>
          </div>
        </div>
        <form className="row row--between" onSubmit={submit}>
          <div className="segmented" role="radiogroup" aria-label="Сайт">
            <button type="button" className="segmented__item" role="radio" aria-checked="true">
              <Icon name="globe" />
              animego
            </button>
            <button type="button" className="segmented__item" role="radio" aria-checked="false" disabled style={{ opacity: 0.5 }}>
              Кинопоиск, позже
            </button>
          </div>
          <div className="row" style={{ flex: "1 1 420px", justifyContent: "flex-end" }}>
            <label className="field" style={{ flex: "1 1 320px", maxWidth: 520, minHeight: 48 }}>
              <Icon name="search" />
              <input
                type="search"
                placeholder="Название на русском, английском или ромадзи"
                aria-label="Искать на animego"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                autoFocus={!queryFromUrl()}
              />
            </label>
            <button className="btn btn--primary" type="submit" disabled={busy || !query.trim()}>
              {busy ? "Ищу…" : "Найти"}
            </button>
          </div>
        </form>
        {!searched && !busy && (
          <div className="chips chips--m-scroll" style={{ marginTop: 20 }}>
            {EXAMPLES.map((ex) => (
              <button
                key={ex}
                className="chip"
                aria-pressed="false"
                onClick={() => {
                  setQuery(ex);
                  void search(ex);
                }}
              >
                {ex}
              </button>
            ))}
          </div>
        )}
      </section>

      {error && (
        <Notice
          title="animego ответил не так, как обычно"
          text={`${error}. Сохранённое в кинотеатре не пострадает. Попробуйте ещё раз чуть позже.`}
          onClose={() => setError(null)}
        />
      )}

      {results && (
        <section className="card">
          <div className="section-head">
            <h2 className="label">Нашлось на animego</h2>
            <span className="small muted">
              {results.length ? `${results.length} по запросу «${searched}»` : `По запросу «${searched}» ничего нет`}
            </span>
          </div>
          {results.length === 0 ? (
            <p className="muted">Попробуйте другое написание: оригинальное название или часть слова.</p>
          ) : (
            <div className="tiles">
              {results.map((t) => (
                <div className="tile" key={t.id}>
                  <Link className="poster" to={R.catalogTitle(t.id)} aria-label={t.title}>
                    <PosterArt id={t.id} title={t.title} src={t.poster} />
                    {t.saved && (
                      <span className="poster__badge">
                        <Icon name="check" />В кинотеатре
                      </span>
                    )}
                  </Link>
                  <Link className="tile__name" to={R.catalogTitle(t.id)} style={{ color: "inherit", textDecoration: "none" }}>
                    {t.title}
                  </Link>
                  <span className="tile__meta">
                    {[t.kind, t.year, t.rating && `★ ${t.rating}`].filter(Boolean).join(", ")}
                  </span>
                  <div className="tile__actions">
                    <Link className="btn btn--small" to={R.catalogTitle(t.id)}>
                      Открыть
                    </Link>
                    <button
                      className="icon-btn icon-btn--neutral"
                      onClick={() => toggleSaved(t)}
                      disabled={saving === t.id}
                      aria-label={t.saved ? "Убрать из кинотеатра" : "Сохранить в кинотеатр"}
                      title={t.saved ? "Убрать из кинотеатра" : "Сохранить в кинотеатр"}
                    >
                      <Icon name={t.saved ? "check" : "bookmark"} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      )}
    </main>
  );
}
