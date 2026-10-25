import { useTheme } from "../theme";
import type { ThemeChoice } from "../theme";
import { Icon } from "./Icons";
import type { IconName } from "./Icons";

const OPTIONS: { value: ThemeChoice; label: string; icon: IconName }[] = [
  { value: "light", label: "Светлая", icon: "sun" },
  { value: "dark", label: "Тёмная", icon: "moon" },
  { value: "system", label: "Как в системе", icon: "auto" },
];

export function ThemeSwitch() {
  const [choice, setChoice] = useTheme();
  return (
    <div className="segmented segmented--icons" role="radiogroup" aria-label="Тема оформления">
      {OPTIONS.map((o) => (
        <button
          key={o.value}
          role="radio"
          aria-checked={choice === o.value}
          aria-label={o.label}
          className="segmented__item"
          onClick={() => setChoice(o.value)}
          title={o.label}
        >
          <Icon name={o.icon} />
        </button>
      ))}
    </div>
  );
}
