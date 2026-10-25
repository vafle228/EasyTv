import { useEffect } from "react";
import type { ReactNode } from "react";
import { AppBar, TabBar } from "./components/AppBar";
import { AddPage } from "./demo/AddPage";
import { LivePage } from "./demo/LivePage";
import { TorrentPage } from "./demo/TorrentPage";
import { useNowPlaying } from "./nowPlaying";
import { CatalogPage } from "./pages/CatalogPage";
import { CinemaPage } from "./pages/CinemaPage";
import { DownloadsPage } from "./pages/DownloadsPage";
import { MainPage } from "./pages/MainPage";
import { PickDialog } from "./pages/PickDialog";
import { RemotePage } from "./pages/RemotePage";
import { TitlePage } from "./pages/TitlePage";
import { TvPage } from "./pages/TvPage";
import { WatchPage } from "./pages/WatchPage";
import { R } from "./routes";
import { Link, useRouter } from "./router";

/** Regular page: app bar on top, section bar at the bottom on phones. */
function Shell({ children }: { children: ReactNode }) {
  return (
    <div className="shell">
      <AppBar />
      {children}
      <TabBar />
    </div>
  );
}

const param = (re: RegExp, path: string) => {
  const m = re.exec(path);
  return m ? (m[1] ? decodeURIComponent(m[1]) : null) : undefined;
};

export function App() {
  const { path: location, navigate } = useRouter();
  const path = location.split("?")[0];
  const back = () => (window.history.length > 1 ? window.history.back() : navigate(R.main));

  // phone screens: no app bar, their own bottom bar
  const remote = param(/^\/remote(?:\/([^/]+))?\/?$/, path);
  if (remote !== undefined) return <RemotePage tvId={remote} />;
  const site = /^\/watch\/animego\/([^/]+)\/(\d+)\/([^/]+)(?:\/([^/]+))?\/?$/.exec(path);
  if (site) {
    const ref = {
      titleId: decodeURIComponent(site[1]),
      episode: Number(site[2]),
      translationId: decodeURIComponent(site[3]),
      provider: site[4] ? decodeURIComponent(site[4]) : "auto",
    };
    return <WatchPage key={path} videoId={null} stream={ref} />;
  }
  const watch = param(/^\/watch(?:\/([^/]+))?\/?$/, path);
  if (watch !== undefined) return <WatchPage videoId={watch} />;

  const pick = param(/^\/pick(?:\/([^/]+))?\/?$/, path);
  if (pick !== undefined) {
    return (
      <>
        <Shell>
          <MainPage />
        </Shell>
        <PickDialog videoId={pick} onClose={back} />
      </>
    );
  }

  const tvId = param(/^\/tv\/([^/]+)\/?$/, path);
  const titleId = param(/^\/catalog\/([^/]+)\/?$/, path);
  let page: ReactNode;
  if (path === R.main) page = <MainPage />;
  else if (tvId) page = <TvPage key={tvId} tvId={tvId} />;
  else if (path === R.tv) page = <TvRedirect />;
  else if (path === R.downloads) page = <DownloadsPage />;
  else if (path === R.add) page = <AddPage />;
  else if (path === R.torrent) page = <TorrentPage />;
  else if (path === R.cinema) page = <CinemaPage />;
  else if (path === R.catalog) page = <CatalogPage />;
  else if (titleId) page = <TitlePage key={titleId} titleId={titleId} />;
  else if (path === R.live) page = <LivePage />;
  else page = <NotFound />;

  return <Shell>{page}</Shell>;
}

/** "/tv": the TV that is playing now, or the first one online. */
function TvRedirect() {
  const { navigate } = useRouter();
  const { tvs, current } = useNowPlaying();
  useEffect(() => {
    if (tvs === null) return;
    const target = current?.tv ?? tvs.find((t) => t.online) ?? tvs[0];
    navigate(target ? R.tvOf(target.id) : R.main, { replace: true });
  }, [tvs, current, navigate]);
  return (
    <main className="page">
      <p className="muted">Ищу телевизор…</p>
    </main>
  );
}

function NotFound() {
  return (
    <main className="page">
      <section className="card">
        <h2 className="label">Такой страницы нет</h2>
        <p className="muted">
          <Link to={R.main}>Вернуться к списку телевизоров</Link>
        </p>
      </section>
    </main>
  );
}
