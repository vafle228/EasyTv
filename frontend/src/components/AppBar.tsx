import { useNowPlaying } from "../nowPlaying";
import { R } from "../routes";
import { Link, useRouter } from "../router";
import { Icon } from "./Icons";
import type { IconName } from "./Icons";
import { ThemeSwitch } from "./ThemeSwitch";

export type Section = "main" | "cinema" | "catalog" | "live" | "downloads";

const SECTIONS: { key: Section; to: string; icon: IconName; label: string; short: string }[] = [
  { key: "main", to: R.main, icon: "tv", label: "Телевизоры", short: "ТВ" },
  { key: "cinema", to: R.cinema, icon: "film", label: "Кинотеатр", short: "Кино" },
  { key: "catalog", to: R.catalog, icon: "globe", label: "Каталоги", short: "Сайты" },
  { key: "live", to: R.live, icon: "live", label: "Эфир", short: "Эфир" },
  { key: "downloads", to: R.downloads, icon: "download", label: "Загрузки", short: "Загрузки" },
];

/** Which section a path belongs to, for the highlighted nav item. */
export function sectionOf(path: string): Section {
  if (path.startsWith("/cinema") || path.startsWith("/watch")) return "cinema";
  if (path.startsWith("/catalog")) return "catalog";
  if (path.startsWith("/live")) return "live";
  if (path.startsWith("/downloads") || path.startsWith("/add")) return "downloads";
  return "main";
}

function useDownloadCount() {
  const { videos } = useNowPlaying();
  return videos?.filter((v) => v.status === "downloading" || v.status === "pending").length ?? 0;
}

export function AppBar() {
  const { path } = useRouter();
  const current = sectionOf(path);
  const downloads = useDownloadCount();
  return (
    <header className="appbar">
      <Link to={R.main} className="brand" aria-label="EasyTv, на главную">
        <span className="brand__name">
          Easy <span className="brand__slash">/</span> Tv
        </span>
        <span className="brand__tagline">Видео на телевизор</span>
      </Link>
      <nav className="nav" aria-label="Разделы">
        {SECTIONS.map((s) => (
          <Link key={s.key} to={s.to} className="nav__item" aria-current={s.key === current ? "page" : undefined}>
            <Icon name={s.icon} />
            {s.label}
            {s.key === "downloads" && downloads > 0 && <span className="nav__count">{downloads}</span>}
          </Link>
        ))}
      </nav>
      <ThemeSwitch />
    </header>
  );
}

/** Bottom section bar. The `page` variant sits under regular pages and CSS shows it only on narrow screens. */
export function TabBar({ page = true }: { page?: boolean }) {
  const { path } = useRouter();
  const current = sectionOf(path);
  return (
    <nav className={page ? "tabbar tabbar--page" : "tabbar"} aria-label="Разделы">
      {SECTIONS.map((s) => (
        <Link key={s.key} to={s.to} aria-current={s.key === current ? "page" : undefined}>
          <Icon name={s.icon} />
          {s.short}
        </Link>
      ))}
    </nav>
  );
}
