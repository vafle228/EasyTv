import { useCallback, useState } from "react";
import { api } from "./api";
import { usePolling } from "./hooks";
import type { PlaybackState, Video } from "./types";

export const STATE_LABEL: Record<PlaybackState, string> = {
  playing: "Играет",
  paused: "На паузе",
  stopped: "Ничего не играет",
  transitioning: "Запускается…",
  no_media: "Ничего не играет",
  unknown: "Телевизор не отвечает",
};

/** Everything a remote needs for one TV: its info, playback, the library and the play/pause/stop commands. */
export function useRemote(tvId: string) {
  const tv = usePolling(() => api.tv(tvId), 10000, tvId);
  const playback = usePolling(() => api.playback(tvId), 2000, tvId);
  const videos = usePolling(api.videos, 2000);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const run = useCallback(
    async (action: () => Promise<unknown>) => {
      setBusy(true);
      setError(null);
      try {
        await action();
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        setBusy(false);
        void playback.reload();
      }
    },
    [playback],
  );

  const state = playback.data?.state ?? "unknown";
  const active = state === "playing" || state === "paused" || state === "transitioning";
  const position = playback.data?.positionS ?? null;
  const duration = playback.data?.durationS ?? null;
  const current: Video | undefined = videos.data?.find((v) => v.id === playback.data?.videoId);

  return {
    tv,
    videos,
    error,
    setError,
    busy,
    run,
    state,
    active,
    position,
    duration,
    current,
    percent: duration && position != null ? Math.min(100, (position / duration) * 100) : 0,
    pause: () => run(() => api.pause(tvId)),
    resume: () => run(() => api.resume(tvId)),
    stop: () => run(() => api.stop(tvId)),
    play: (video: Video) => run(() => api.play(tvId, video.id)),
  };
}
