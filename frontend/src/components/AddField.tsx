import { useState } from "react";
import type { FormEvent } from "react";
import { api } from "../api";
import { detectSource, NOT_YET } from "../detect";
import { Icon } from "./Icons";

interface Props {
  onAdded: () => void;
  onError: (message: string) => void;
}

/** The one "Добавить" field for every source. YouTube downloads for real; other kinds explain they're coming. */
export function AddField({ onAdded, onError }: Props) {
  const [value, setValue] = useState("");
  const [adding, setAdding] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const url = value.trim();
    if (!url) return;
    const kind = detectSource(url);
    if (kind !== "youtube") {
      onError(NOT_YET[kind]);
      return;
    }
    setAdding(true);
    try {
      await api.addYoutube(url);
      setValue("");
      onAdded();
    } catch (err) {
      onError(err instanceof Error ? err.message : String(err));
    } finally {
      setAdding(false);
    }
  };

  return (
    <form className="add" onSubmit={submit}>
      <label className="field">
        <Icon name="link" />
        <input
          type="text"
          inputMode="url"
          placeholder="Ссылка на YouTube, magnet, .m3u8 или страницу на animego"
          aria-label="Что добавить"
          value={value}
          onChange={(e) => setValue(e.target.value)}
        />
      </label>
      <button className="btn btn--primary" type="submit" disabled={adding || !value.trim()}>
        <Icon name="plus" />
        {adding ? "Добавляю…" : "Добавить"}
      </button>
    </form>
  );
}
