import type { StreamRef } from "./types";

const enc = encodeURIComponent;

/** Paths of every screen. Demo sections (live, torrents) still use sample data until their backend exists. */
export const R = {
  main: "/",
  /** The TV that is playing now, or the first one online (see TvRedirect). */
  tv: "/tv",
  tvOf: (id: string) => `/tv/${enc(id)}`,
  pick: "/pick",
  pickFor: (videoId: string) => `/pick/${enc(videoId)}`,
  phone: "/remote",
  phoneOf: (tvId: string) => `/remote/${enc(tvId)}`,
  watch: "/watch",
  watchOf: (videoId: string) => `/watch/${enc(videoId)}`,
  /** An episode from a site, played in this browser through the server's proxy. */
  watchStream: (r: StreamRef) =>
    `/watch/animego/${enc(r.titleId)}/${r.episode}/${enc(r.translationId)}` +
    (r.provider && r.provider !== "auto" ? `/${enc(r.provider)}` : ""),
  add: "/add",
  torrent: "/add/torrent",
  downloads: "/downloads",
  cinema: "/cinema",
  catalog: "/catalog",
  catalogSearch: (q: string) => `/catalog?q=${enc(q)}`,
  catalogTitle: (id: string) => `/catalog/${enc(id)}`,
  live: "/live",
} as const;
