/** Paths of every screen. Demo sections (cinema, catalogs, live, torrents) use fixed sample slugs until their backend exists. */
export const R = {
  main: "/",
  /** The TV that is playing now, or the first one online (see TvRedirect). */
  tv: "/tv",
  tvOf: (id: string) => `/tv/${encodeURIComponent(id)}`,
  pick: "/pick",
  pickFor: (videoId: string) => `/pick/${encodeURIComponent(videoId)}`,
  phone: "/remote",
  phoneOf: (tvId: string) => `/remote/${encodeURIComponent(tvId)}`,
  watch: "/watch",
  watchOf: (videoId: string) => `/watch/${encodeURIComponent(videoId)}`,
  add: "/add",
  torrent: "/add/torrent",
  downloads: "/downloads",
  cinema: "/cinema",
  title: "/cinema/frieren",
  film: "/cinema/dune-part-two",
  catalog: "/catalog",
  sourceTitle: "/catalog/naruto-shippuden",
  voice: "/catalog/naruto-shippuden/voice",
  live: "/live",
} as const;
