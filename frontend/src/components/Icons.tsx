const base = { width: 18, height: 18, viewBox: "0 0 24 24", fill: "none", "aria-hidden": true } as const;
const stroke = { stroke: "currentColor", strokeWidth: 2, strokeLinecap: "round", strokeLinejoin: "round" } as const;

export const PlayIcon = () => (
  <svg {...base}>
    <path d="M8 5.5v13l10.5-6.5z" fill="currentColor" />
  </svg>
);
export const PauseIcon = () => (
  <svg {...base}>
    <rect x="6.5" y="5" width="4" height="14" rx="1.5" fill="currentColor" />
    <rect x="13.5" y="5" width="4" height="14" rx="1.5" fill="currentColor" />
  </svg>
);
export const StopIcon = () => (
  <svg {...base}>
    <rect x="6" y="6" width="12" height="12" rx="2.5" fill="currentColor" />
  </svg>
);
export const RefreshIcon = () => (
  <svg {...base}>
    <path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7" {...stroke} />
  </svg>
);
export const BackIcon = () => (
  <svg {...base}>
    <path d="M15 5l-7 7 7 7" {...stroke} />
  </svg>
);
export const TrashIcon = () => (
  <svg {...base}>
    <path d="M4 7h16M10 11v6M14 11v6M6 7l1 12h10l1-12M9 7V4h6v3" {...stroke} />
  </svg>
);
export const UploadIcon = () => (
  <svg {...base}>
    <path d="M12 16V4M7 9l5-5 5 5M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3" {...stroke} />
  </svg>
);
export const LinkIcon = () => (
  <svg {...base}>
    <path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1" {...stroke} />
  </svg>
);
export const SunIcon = () => (
  <svg {...base}>
    <circle cx="12" cy="12" r="4" {...stroke} />
    <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" {...stroke} />
  </svg>
);
export const MoonIcon = () => (
  <svg {...base}>
    <path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z" {...stroke} />
  </svg>
);
export const AutoIcon = () => (
  <svg {...base}>
    <circle cx="12" cy="12" r="8" {...stroke} />
    <path d="M12 4a8 8 0 0 1 0 16z" fill="currentColor" />
  </svg>
);
export const BellIcon = () => (
  <svg {...base}>
    <path d="M6 16V11a6 6 0 1 1 12 0v5l1.5 2h-15zM10 20a2 2 0 0 0 4 0" fill="currentColor" />
  </svg>
);
export const CloseIcon = () => (
  <svg {...base}>
    <path d="M6 6l12 12M18 6L6 18" {...stroke} />
  </svg>
);
export const PlusIcon = () => (
  <svg {...base}>
    <path d="M12 5v14M5 12h14" {...stroke} />
  </svg>
);
export const YoutubeIcon = () => (
  <svg {...base}>
    <rect x="2.5" y="5.5" width="19" height="13" rx="4" fill="currentColor" />
    <path d="M10 9.2v5.6l4.8-2.8z" fill="var(--yt-play, #fff)" />
  </svg>
);
export const FileIcon = () => (
  <svg {...base}>
    <path d="M6 3h8l4 4v14H6z" fill="currentColor" />
    <path d="M10 11v6l5-3z" fill="var(--yt-play, #fff)" />
  </svg>
);
