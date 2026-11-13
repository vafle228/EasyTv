import { useCallback, useRef, useState } from "react";
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

/** Everything a remote needs for one TV: its info, playback, the library and the playback commands. */
export function useRemote(tvId: string) {
  const tv = usePolling(() => api.tv(tvId), 10000, tvId);
  const playback = usePolling(() => api.playback(tvId), 2000, tvId);
  const videos = usePolling(api.videos, 2000);
  const queue = usePolling(() => api.queue(tvId), 2000, tvId);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const pending = useRef(false);

  const run = useCallback(
    async (action: () => Promise<unknown>) => {
      if (pending.current) return;
      pending.current = true;
      setBusy(true);
      setError(null);
      try {
        await action();
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        await Promise.all([playback.reload(), queue.reload()]);
        pending.current = false;
        setBusy(false);
      }
    },
    [playback, queue],
  );

  const state = playback.data?.state ?? "unknown";
  const active = state === "playing" || state === "paused" || state === "transitioning";
  const position = playback.data?.positionS ?? null;
  const duration = playback.data?.durationS ?? null;
  const canSeek = !playback.error && playback.data?.seekable !== false && (state === "playing" || state === "paused");
  const current: Video | undefined = videos.data?.find((v) => v.id === playback.data?.videoId);
  const title = current?.title ?? playback.data?.title ?? null;
  const nextItem = queue.data?.items[0];

  return {
    tv,
    videos,
    queue,
    error: error ?? playback.data?.error ?? null,
    setError,
    busy,
    run,
    state,
    active,
    position,
    duration,
    current,
    title,
    canSeekTo: canSeek && duration !== null && duration > 0,
    canSeekBy: canSeek && position !== null,
    seekTo: (positionS: number) => run(() => api.seek(tvId, { positionS })),
    seekBy: (offsetS: number) => run(() => api.seek(tvId, { offsetS })),
    pause: () => run(() => api.pause(tvId)),
    resume: () => run(() => api.resume(tvId)),
    stop: () => run(() => api.stop(tvId)),
    canPlayNext: !!nextItem && !queue.error && !!tv.data?.online,
    playNext: () => nextItem && run(() => api.next(tvId, nextItem.id)),
    enqueue: (video: Video) => run(() => api.enqueue(tvId, { videoId: video.id })),
    removeQueued: (itemId: string) => run(() => api.removeQueued(tvId, itemId)),
    play: (video: Video) => run(() => api.play(tvId, video.id)),
  };
}
