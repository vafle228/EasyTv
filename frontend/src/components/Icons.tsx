import type { ReactNode } from "react";

/** Design-system icons: 24×24 grid, 2px line; `.f` parts are filled, `.yp` is the play mark inside YouTube/file badges. */
const ICONS = {
  play: <path className="f" d="M8 5.5v13l10.5-6.5z" />,
  pause: (
    <>
      <rect className="f" x="6.5" y="5" width="4" height="14" rx="1.5" />
      <rect className="f" x="13.5" y="5" width="4" height="14" rx="1.5" />
    </>
  ),
  stop: <rect className="f" x="6" y="6" width="12" height="12" rx="2.5" />,
  refresh: <path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7" />,
  back: <path d="M15 5l-7 7 7 7" />,
  trash: <path d="M4 7h16M10 11v6M14 11v6M6 7l1 12h10l1-12M9 7V4h6v3" />,
  upload: <path d="M12 16V4M7 9l5-5 5 5M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3" />,
  link: <path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1" />,
  sun: (
    <>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
    </>
  ),
  moon: <path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z" />,
  auto: (
    <>
      <circle cx="12" cy="12" r="8" />
      <path className="f" d="M12 4a8 8 0 0 1 0 16z" />
    </>
  ),
  bell: <path className="f" d="M6 16V11a6 6 0 1 1 12 0v5l1.5 2h-15zM10 20a2 2 0 0 0 4 0" />,
  close: <path d="M6 6l12 12M18 6L6 18" />,
  plus: <path d="M12 5v14M5 12h14" />,
  youtube: (
    <>
      <rect className="f" x="2.5" y="5.5" width="19" height="13" rx="4" />
      <path className="yp" d="M10 9.2v5.6l4.8-2.8z" />
    </>
  ),
  file: (
    <>
      <path className="f" d="M6 3h8l4 4v14H6z" />
      <path className="yp" d="M10 11v6l5-3z" />
    </>
  ),
  search: (
    <>
      <circle cx="11" cy="11" r="7" />
      <path d="M20 20l-3.5-3.5" />
    </>
  ),
  tv: (
    <>
      <rect x="3" y="5" width="18" height="12" rx="3" />
      <path d="M9 21h6" />
    </>
  ),
  film: (
    <>
      <rect x="3" y="4" width="18" height="16" rx="3" />
      <path d="M8 4v16M16 4v16M3 9h5M3 15h5M16 9h5M16 15h5" />
    </>
  ),
  globe: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18" />
    </>
  ),
  live: (
    <>
      <circle className="f" cx="12" cy="12" r="2.5" />
      <path d="M7.8 7.8a6 6 0 0 0 0 8.4M16.2 7.8a6 6 0 0 1 0 8.4M5 5a10 10 0 0 0 0 14M19 5a10 10 0 0 1 0 14" />
    </>
  ),
  download: <path d="M12 4v11M7 10l5 5 5-5M4 20h16" />,
  magnet: (
    <>
      <path d="M6 4h4v7a2 2 0 0 0 4 0V4h4v7a6 6 0 0 1-12 0z" />
      <path d="M6 8h4M14 8h4" />
    </>
  ),
  check: <path d="M5 12.5l4.5 4.5L19 7.5" />,
  minus: <path d="M6 12h12" />,
  bookmark: <path d="M7 4h10v16l-5-4-5 4z" />,
  next: (
    <>
      <path className="f" d="M5.5 5.5v13l9.5-6.5z" />
      <rect className="f" x="16" y="5" width="3" height="14" rx="1.4" />
    </>
  ),
  prev: (
    <>
      <path className="f" d="M18.5 5.5v13L9 12z" />
      <rect className="f" x="5" y="5" width="3" height="14" rx="1.4" />
    </>
  ),
  back10: <path d="M4 12a8 8 0 1 0 2.4-5.7M4 4v5h5" />,
  fwd10: <path d="M20 12a8 8 0 1 1-2.4-5.7M20 4v5h-5" />,
  volume: (
    <>
      <path className="f" d="M4 9.5h3.5L12 6v12l-4.5-3.5H4z" />
      <path d="M15.5 9a4 4 0 0 1 0 6M18 6.5a7.5 7.5 0 0 1 0 11" />
    </>
  ),
  phone: (
    <>
      <rect x="7" y="3" width="10" height="18" rx="2.5" />
      <path d="M11 18h2" />
    </>
  ),
  queue: (
    <>
      <path d="M4 6h16M4 12h16M4 18h9" />
      <path d="M17 16v5l4-2.5z" />
    </>
  ),
  folder: <path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />,
  star: <path className="f" d="M12 3.8l2.5 5.1 5.6.8-4 3.9 1 5.6-5.1-2.7-5 2.7 1-5.6-4.1-3.9 5.6-.8z" />,
  chevron: <path d="M6 9l6 6 6-6" />,
  edit: <path d="M4 20h4L19 9l-4-4L4 16zM13.5 6.5l4 4" />,
  list: (
    <>
      <path d="M9 6h11M9 12h11M9 18h11" />
      <circle className="f" cx="4.5" cy="6" r="1.5" />
      <circle className="f" cx="4.5" cy="12" r="1.5" />
      <circle className="f" cx="4.5" cy="18" r="1.5" />
    </>
  ),
  subs: (
    <>
      <rect x="3" y="5" width="18" height="14" rx="3" />
      <path d="M7 13h4M13 13h4M7 16h7" />
    </>
  ),
  cog: (
    <>
      <circle cx="12" cy="12" r="3" />
      <path d="M12 3v2.5M12 18.5V21M3 12h2.5M18.5 12H21M5.6 5.6l1.8 1.8M16.6 16.6l1.8 1.8M5.6 18.4l1.8-1.8M16.6 7.4l1.8-1.8" />
    </>
  ),
} satisfies Record<string, ReactNode>;

export type IconName = keyof typeof ICONS;

export function Icon({ name }: { name: IconName }) {
  return (
    <svg className="i" width="18" height="18" viewBox="0 0 24 24" aria-hidden="true">
      {ICONS[name]}
    </svg>
  );
}
