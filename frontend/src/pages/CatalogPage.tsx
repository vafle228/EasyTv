import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { api } from "../api";
import { Icon } from "../components/Icons";
import { Notice } from "../components/Notice";
import { PosterArt } from "../components/Poster";
import { R } from "../routes";
import { Link } from "../router";
import type { CatalogTitle, Collection } from "../types";

const params = () => new URLSearchParams(window.location.search);

/** Catalogs: animego's lists (ongoing, this season…) to browse, search, open a title, keep it in the cinema. */
export function CatalogPage() {
  const [query, setQuery] = useState(() => params().get("q") ?? "");
  const [searched, setSearched] = useState<string | null>(null);
  const [results, setResults] = useState<CatalogTitle[] | null>(null);
  const [collections, setCollections] = useState<Collection[] | null>(null);
  const [shelf, setShelf] = useState<string | null>(() => params().get("c"));
  const [items, setItems] = useState<CatalogTitle[] | null>(null);
  const [page, setPage] = useState(1);
  const [more, setMore] = useState(true);
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

  const clearSearch = () => {
    setQuery("");
    setResults(null);
    setSearched(null);
    window.history.replaceState(null, "", shelf ? `${R.catalog}?c=${encodeURIComponent(shelf)}` : R.catalog);
  };

  useEffect(() => {
    const q = params().get("q");
    if (q) void search(q);
    api
      .collections()
      .then((cs) => {
        setCollections(cs);
        setShelf((cur) => (cur && cs.some((c) => c.id === cur) ? cur : (cs[0]?.id ?? null)));
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

  // A shelf loads page by page; switching shelves starts over.
  const loadShelf = async (id: string, p: number) => {
    setBusy(true);
    setError(null);
    try {
      const got = await api.collection(id, p);
      setItems((cur) => (p === 1 ? got : [...(cur ?? []), ...got.filter((g) => !cur?.some((c) => c.id === g.id))]));
      setPage(p);
      setMore(got.length > 0);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    if (!shelf) return;
    setItems(null);
    void loadShelf(shelf, 1);
  }, [shelf]);

  const pickShelf = (id: string) => {
    setShelf(id);
    if (!searched) window.history.replaceState(null, "", `${R.catalog}?c=${encodeURIComponent(id)}`);
  };

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (query.trim()) void search(query);
    else clearSearch();
  };

  const toggleSaved = async (t: CatalogTitle) => {
    setSaving(t.id);
    setError(null);
    try {
      if (t.saved) await api.unsaveTitle(t.id);
      else await api.saveTitle(t.id);
      const flip = (list: CatalogTitle[] | null) => list?.map((r) => (r.id === t.id ? { ...r, saved: !t.saved } : r)) ?? null;
      setResults(flip);
      setItems(flip);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(null);
    }
  };

  const current = collections?.find((c) => c.id === shelf);

  return (
    <main className="page">
      <section className="card">
        <div className="card__head" style={{ marginBottom: 22 }}>
          <div>
            <h1 className="label">Каталоги</h1>
            <p className="muted">
              Листайте animego или найдите аниме по названию, смотрите серии в браузере или на телевизоре. Понравившееся
              сохраните в кинотеатр: там запомнится, где вы остановились.
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
                onChange={(e) => {
                  setQuery(e.target.value);
                  if (!e.target.value && searched) clearSearch();
                }}
              />
            </label>
            <button className="btn btn--primary" type="submit" disabled={busy || !query.trim()}>
              {busy && query.trim() && query.trim() !== searched ? "Ищу…" : "Найти"}
            </button>
          </div>
        </form>
        {!searched && collections && (
          <div className="chips chips--m-scroll" style={{ marginTop: 20 }} role="radiogroup" aria-label="Подборка">
            {collections.map((c) => (
              <button key={c.id} className="chip" aria-pressed={c.id === shelf} onClick={() => pickShelf(c.id)}>
                {c.title}
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

      {searched && results && (
        <section className="card">
          <div className="section-head">
            <h2 className="label">Нашлось на animego</h2>
            <button className="link" style={{ border: 0, background: "none", cursor: "pointer" }} onClick={clearSearch}>
              К подборкам
            </button>
          </div>
          {results.length === 0 ? (
            <p className="muted">
              По запросу «{searched}» ничего нет. Попробуйте другое написание: оригинальное название или часть слова.
            </p>
          ) : (
            <Tiles items={results} saving={saving} onToggle={toggleSaved} />
          )}
        </section>
      )}

      {!searched && current && (
        <section className="card">
          <div className="section-head">
            <h2 className="label">{current.title}</h2>
            <span className="small muted">animego</span>
          </div>
          {items === null ? (
            <p className="muted">Загружаю подборку…</p>
          ) : items.length === 0 ? (
            <p className="muted">В этой подборке пока пусто.</p>
          ) : (
            <>
              <Tiles items={items} saving={saving} onToggle={toggleSaved} />
              {more && (
                <div className="row" style={{ justifyContent: "center", marginTop: 28 }}>
                  <button className="btn" onClick={() => shelf && loadShelf(shelf, page + 1)} disabled={busy}>
                    {busy ? "Загружаю…" : "Загрузить ещё"}
                  </button>
                </div>
              )}
            </>
          )}
        </section>
      )}
    </main>
  );
}

function Tiles({
  items,
  saving,
  onToggle,
}: {
  items: CatalogTitle[];
  saving: string | null;
  onToggle: (t: CatalogTitle) => void;
}) {
  return (
    <div className="tiles">
      {items.map((t) => (
        <div className="tile" key={t.id}>
          <Link className="poster" to={R.catalogTitle(t.id)} aria-label={t.title}>
            <PosterArt id={t.id} title={t.title} src={t.poster} />
            {t.saved ? (
              <span className="poster__badge">
                <Icon name="check" />В кинотеатре
              </span>
            ) : (
              t.rating && <span className="poster__badge">★ {t.rating}</span>
            )}
          </Link>
          <Link className="tile__name" to={R.catalogTitle(t.id)} style={{ color: "inherit", textDecoration: "none" }}>
            {t.title}
          </Link>
          <span className="tile__meta">{[t.kind, t.year].filter(Boolean).join(", ")}</span>
          <div className="tile__actions">
            <Link className="btn btn--small" to={R.catalogTitle(t.id)}>
              Открыть
            </Link>
            <button
              className="icon-btn icon-btn--neutral"
              onClick={() => onToggle(t)}
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
  );
}
