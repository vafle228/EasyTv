import type { ReactNode } from "react";

interface Props {
  on: boolean;
  size?: "card" | "hero";
  children?: ReactNode;
}

/** A soft, drawn TV set. The screen glows when the TV is reachable and goes dark when it isn't. */
export function TvScreen({ on, size = "card", children }: Props) {
  return (
    <div className={`tv tv--${size} ${on ? "tv--on" : "tv--off"}`}>
      <div className="tv__frame">
        <div className="tv__screen">{children}</div>
      </div>
      <div className="tv__stand" aria-hidden />
    </div>
  );
}
