import { BellIcon, CloseIcon } from "./Icons";

interface Props {
  title: string;
  text?: string | null;
  tone?: "error" | "info";
  onClose?: () => void;
}

/** Notification card from the design system: icon bubble, title, text, dismiss. */
export function Notice({ title, text, tone = "error", onClose }: Props) {
  return (
    <div className={`notice notice--${tone}`} role={tone === "error" ? "alert" : "status"}>
      <span className="notice__icon">
        <BellIcon />
      </span>
      <div className="notice__body">
        <strong>{title}</strong>
        {text && <p>{text}</p>}
      </div>
      {onClose && (
        <button className="icon-btn icon-btn--flat" onClick={onClose} aria-label="Скрыть">
          <CloseIcon />
        </button>
      )}
    </div>
  );
}
