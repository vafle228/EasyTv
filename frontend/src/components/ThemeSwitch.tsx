import type { ReactNode } from "react";
import { useTheme } from "../theme";
import type { ThemeChoice } from "../theme";
import { AutoIcon, MoonIcon, SunIcon } from "./Icons";

const OPTIONS: { value: ThemeChoice; label: string; icon: ReactNode }[] = [
  { value: "light", label: "Светлая", icon: <SunIcon /> },
  { value: "dark", label: "Тёмная", icon: <MoonIcon /> },
  { value: "system", label: "Как в системе", icon: <AutoIcon /> },
];

export function ThemeSwitch() {
  const [choice, setChoice] = useTheme();
  return (
    <div className="segmented" role="radiogroup" aria-label="Тема оформления">
      {OPTIONS.map((o) => (
        <button
          key={o.value}
          role="radio"
          aria-checked={choice === o.value}
          className="segmented__item"
          onClick={() => setChoice(o.value)}
          title={o.label}
        >
          {o.icon}
          <span className="segmented__label">{o.label}</span>
        </button>
      ))}
    </div>
  );
}
