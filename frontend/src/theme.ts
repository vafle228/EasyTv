import { useEffect, useState } from "react";

export type ThemeChoice = "light" | "dark" | "system";

const KEY = "easytv-theme";
const media = () => window.matchMedia("(prefers-color-scheme: dark)");

function readChoice(): ThemeChoice {
  try {
    const value = localStorage.getItem(KEY);
    if (value === "light" || value === "dark" || value === "system") return value;
  } catch {
    /* storage may be unavailable */
  }
  return "system";
}

function apply(choice: ThemeChoice) {
  const dark = choice === "dark" || (choice === "system" && media().matches);
  document.documentElement.dataset.theme = dark ? "dark" : "light";
}

/** Light, dark or follow the OS. The choice is remembered in this browser. */
export function useTheme() {
  const [choice, setChoice] = useState<ThemeChoice>(readChoice);

  useEffect(() => {
    apply(choice);
    try {
      localStorage.setItem(KEY, choice);
    } catch {
      /* ignore */
    }
    if (choice !== "system") return;
    const mq = media();
    const onChange = () => apply("system");
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, [choice]);

  return [choice, setChoice] as const;
}
