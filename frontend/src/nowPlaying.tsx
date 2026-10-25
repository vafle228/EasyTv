import { createContext, useContext } from "react";
import type { ReactNode } from "react";
import { api } from "./api";
import { usePolling } from "./hooks";
import type { Playback, Tv, Video } from "./types";

export interface Screen {
  tv: Tv;
  playback: Playback;
  video: Video | undefined;
}

interface NowPlaying {
  tvs: Tv[] | null;
  videos: Video[] | null;
  /** Playback of every TV that is online, by TV id. */
  playback: Record<string, Playback>;
  /** The first TV that is playing or paused: what the "now on screen" bar shows. */
  current: Screen | null;
  error: string | null;
  reload: () => Promise<void>;
}

const Ctx = createContext<NowPlaying>({
  tvs: null,
  videos: null,
  playback: {},
  current: null,
  error: null,
  reload: async () => {},
});

const ACTIVE = new Set(["playing", "paused", "transitioning"]);
export const isActive = (p: Playback | undefined) => !!p && ACTIVE.has(p.state);

async function load() {
  const [tvs, videos] = await Promise.all([api.tvs(), api.videos()]);
  const entries = await Promise.all(
    tvs
      .filter((t) => t.online)
      .map(async (t) => [t.id, await api.playback(t.id).catch(() => null)] as const),
  );
  const playback: Record<string, Playback> = {};
  for (const [id, p] of entries) if (p) playback[id] = p;
  return { tvs, videos, playback };
}

/** One shared poll of TVs, the library and what each TV is showing, for the app bar, the main page and the now bar. */
export function NowPlayingProvider({ children }: { children: ReactNode }) {
  const { data, error, reload } = usePolling(load, 3000);
  const tvs = data?.tvs ?? null;
  const videos = data?.videos ?? null;
  const playback = data?.playback ?? {};
  const tv = tvs?.find((t) => isActive(playback[t.id]));
  const current = tv
    ? { tv, playback: playback[tv.id], video: videos?.find((v) => v.id === playback[tv.id].videoId) }
    : null;
  return (
    <Ctx.Provider value={{ tvs, videos, playback, current, error, reload }}>{children}</Ctx.Provider>
  );
}

export const useNowPlaying = () => useContext(Ctx);
