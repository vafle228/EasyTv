import { useState } from "react";
import type { FormEvent } from "react";
import { api } from "../api";
import { LinkIcon, PlusIcon, RefreshIcon } from "../components/Icons";
import { Notice } from "../components/Notice";
import { TvScreen } from "../components/TvScreen";
import { tvSubtitle } from "../format";
import { usePolling } from "../hooks";
import { Link } from "../router";

export function TvListPage() {
  const { data: tvs, error, setData, reload } = usePolling(api.tvs, 5000);
  const [searching, setSearching] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const [address, setAddress] = useState("");
  const [adding, setAdding] = useState(false);

  const searchNow = async () => {
    setSearching(true);
    setProblem(null);
    try {
      setData(await api.refreshTvs());
    } catch (e) {
      setProblem(e instanceof Error ? e.message : String(e));
    } finally {
      setSearching(false);
    }
  };

  const addTv = async (e: FormEvent) => {
    e.preventDefault();
    if (!address.trim()) return;
    setAdding(true);
    setProblem(null);
    try {
      await api.addTv(address.trim());
      setAddress("");
      await reload();
    } catch (err) {
      setProblem(err instanceof Error ? err.message : String(err));
    } finally {
      setAdding(false);
    }
  };

  const online = tvs?.filter((t) => t.online).length ?? 0;

  return (
    <main className="page">
      <section className="card">
        <div className="card__head">
          <div>
            <h1 className="label">Телевизоры</h1>
            <p className="muted">
              {tvs === null
                ? "Загружаю список…"
                : tvs.length === 0
                  ? "Ищу телевизоры в сети каждые 15 секунд."
                  : `В сети ${online} из ${tvs.length}. Выберите, на каком показать видео.`}
            </p>
          </div>
          <button className="btn" onClick={searchNow} disabled={searching}>
            <span className={searching ? "spin" : undefined}>
              <RefreshIcon />
            </span>
            {searching ? "Ищу…" : "Искать сейчас"}
          </button>
        </div>

        {(problem || error) && (
          <Notice
            title={problem ? "Не получилось" : "Нет связи с сервером"}
            text={problem ?? error}
            onClose={problem ? () => setProblem(null) : undefined}
          />
        )}

        {tvs && tvs.length === 0 && (
          <div className="empty">
            <TvScreen on={false}>
              <span className="tv__hint">нет сигнала</span>
            </TvScreen>
            <div>
              <h2 className="title">Телевизоров пока не видно</h2>
              <p className="muted">
                Включите телевизор и проверьте, что он подключён к тому же роутеру, что и этот компьютер. Если поиск
                его не находит, добавьте телевизор по адресу ниже.
              </p>
            </div>
          </div>
        )}

        {tvs && tvs.length > 0 && (
          <ul className="tv-grid">
            {tvs.map((tv) => (
              <li key={tv.id}>
                <Link to={`/tv/${encodeURIComponent(tv.id)}`} className="tv-card">
                  <TvScreen on={tv.online}>
                    <span className="tv__brand">{tv.manufacturer?.split(" ")[0] ?? "TV"}</span>
                  </TvScreen>
                  <span className="tv-card__name">{tv.name}</span>
                  <span className="tv-card__meta">
                    <span className={`status ${tv.online ? "status--on" : ""}`}>
                      {tv.online ? "В сети" : "Не в сети"}
                    </span>
                    {tvSubtitle(tv.manufacturer, tv.model, tv.ip)}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="card">
        <h2 className="label">Добавить по адресу</h2>
        <p className="muted">
          Если телевизор не находится сам, укажите его IP (например, 192.168.0.72) или адрес описания устройства, который
          показывает <code>./run.sh discover</code>.
        </p>
        <form className="field-row" onSubmit={addTv}>
          <label className="field">
            <LinkIcon />
            <input
              placeholder="192.168.0.72 или http://…"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              aria-label="IP или адрес телевизора"
            />
          </label>
          <button className="btn btn--primary" type="submit" disabled={adding || !address.trim()}>
            <PlusIcon />
            {adding ? "Ищу телевизор…" : "Добавить"}
          </button>
        </form>
      </section>
    </main>
  );
}
