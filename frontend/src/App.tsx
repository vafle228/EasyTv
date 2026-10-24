import { ThemeSwitch } from "./components/ThemeSwitch";
import { Link, useRouter } from "./router";
import { TvListPage } from "./pages/TvListPage";
import { TvPage } from "./pages/TvPage";

export function App() {
  const { path } = useRouter();
  const tvMatch = /^\/tv\/([^/]+)\/?$/.exec(path);

  return (
    <div className="shell">
      <header className="topbar">
        <Link to="/" className="brand" aria-label="EasyTv, на главную">
          <span className="brand__name">
            Easy <span className="brand__slash">/</span> Tv
          </span>
          <span className="brand__tagline">Видео на телевизор</span>
        </Link>
        <ThemeSwitch />
      </header>

      {path === "/" ? (
        <TvListPage />
      ) : tvMatch ? (
        <TvPage key={tvMatch[1]} tvId={decodeURIComponent(tvMatch[1])} />
      ) : (
        <main className="page">
          <section className="card">
            <h2 className="label">Такой страницы нет</h2>
            <p className="muted">
              <Link to="/">Вернуться к списку телевизоров</Link>
            </p>
          </section>
        </main>
      )}
    </div>
  );
}
