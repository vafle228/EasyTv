import { useEffect, useRef } from "react";
import type { ReactNode } from "react";
import { Icon } from "./Icons";

/** Marks a section whose backend is not built yet: the content is sample data from the mockups. */
export function DemoNote({ children }: { children?: ReactNode }) {
  return (
    <p className="demo" role="note">
      <Icon name="star" />
      {children ?? "Раздел в разработке: здесь пример из макетов, бэкенда для него пока нет."}
    </p>
  );
}

/**
 * Makes the static controls of a demo screen respond to clicks without wiring each one:
 * radios inside a radiogroup, toggle chips (aria-pressed) and checkboxes (role="checkbox").
 */
export function useDemoControls<T extends HTMLElement>() {
  const ref = useRef<T>(null);
  useEffect(() => {
    const root = ref.current;
    if (!root) return;
    const onClick = (e: MouseEvent) => {
      const el = (e.target as HTMLElement).closest<HTMLElement>("[role=radio], [aria-pressed], [role=checkbox]");
      if (!el || !root.contains(el) || (el as HTMLButtonElement).disabled) return;
      if (el.getAttribute("role") === "radio") {
        el.closest("[role=radiogroup]")
          ?.querySelectorAll("[role=radio]")
          .forEach((r) => r.setAttribute("aria-checked", String(r === el)));
      } else if (el.hasAttribute("aria-pressed")) {
        el.setAttribute("aria-pressed", String(el.getAttribute("aria-pressed") !== "true"));
      } else {
        el.setAttribute("aria-checked", String(el.getAttribute("aria-checked") !== "true"));
      }
    };
    root.addEventListener("click", onClick);
    return () => root.removeEventListener("click", onClick);
  }, []);
  return ref;
}
