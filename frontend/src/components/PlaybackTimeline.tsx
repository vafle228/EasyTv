import { useEffect, useRef, useState } from "react";
import { formatTime } from "../format";

interface Props {
  position: number | null;
  duration: number | null;
  enabled: boolean;
  busy: boolean;
  onSeek: (seconds: number) => Promise<void>;
}

export function PlaybackTimeline({ position, duration, enabled, busy, onSeek }: Props) {
  const slider = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState<number | null>(null);
  const shown = enabled ? (preview ?? position) : position;

  useEffect(() => {
    const input = slider.current;
    if (!input || !enabled || busy) return;

    // Native change commits a drag once, when the thumb is released.
    const commit = () => {
      const target = input.valueAsNumber;
      setPreview(target);
      void onSeek(target).finally(() => setPreview(null));
    };
    input.addEventListener("change", commit);
    return () => input.removeEventListener("change", commit);
  }, [enabled, busy, onSeek]);

  return (
    <div className="timeline">
      <input
        ref={slider}
        className="timeline__seek"
        type="range"
        min={0}
        max={duration || 1}
        value={Math.min(shown ?? 0, duration ?? 0)}
        disabled={!enabled}
        aria-disabled={busy}
        aria-label="Позиция воспроизведения"
        aria-valuetext={formatTime(shown)}
        onInput={(event) => {
          if (!busy) setPreview(event.currentTarget.valueAsNumber);
          else event.currentTarget.value = String(Math.min(shown ?? 0, duration ?? 0));
        }}
        onPointerCancel={() => setPreview(null)}
      />
      <span className="timeline__time">
        {formatTime(shown)} / {formatTime(duration)}
      </span>
    </div>
  );
}
