import { useEffect, useRef, useState } from "react";
import { ApiError, api } from "../api";

export function NameEditor({ id, name, onSaved, onFailed }: { id: string; name: string; onSaved: (name: string) => void; onFailed: (message: string) => void }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(name);
  const [saving, setSaving] = useState(false);
  const input = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!editing) setDraft(name);
  }, [name, editing]);

  useEffect(() => {
    if (editing) {
      input.current?.focus();
      input.current?.select();
    }
  }, [editing]);

  function cancel() {
    setEditing(false);
    setDraft(name);
  }

  async function save() {
    if (!editing || saving) return;
    const next = draft.trim();
    if (!next || next === name) {
      cancel();
      return;
    }
    setSaving(true);
    try {
      await api(`/api/servers/${id}`, { method: "PATCH", body: JSON.stringify({ name: next }) });
      onSaved(next);
      setEditing(false);
    } catch (err) {
      onFailed(err instanceof ApiError ? err.message : "名称保存失败");
      input.current?.focus();
    } finally {
      setSaving(false);
    }
  }

  return (
    <span className="copy-line" onClick={(event) => event.stopPropagation()}>
      {editing ? (
        <input
          ref={input}
          className="name-edit"
          maxLength={80}
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              void save();
            }
            if (event.key === "Escape") {
              event.preventDefault();
              cancel();
            }
          }}
          onBlur={() => void save()}
        />
      ) : (
        <>
          <span className="name-text">{name}</span>
          <button className="pen" type="button" title="修改名称" onClick={() => { setDraft(name); setEditing(true); }}>
            <svg viewBox="0 0 16 16" aria-hidden="true">
              <path d="M2.8 11.5 2.2 13.8 4.5 13.2 12.7 5 11 3.3 2.8 11.5Z" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
              <path d="M10.1 4.2 11.8 5.9" fill="none" stroke="currentColor" strokeWidth="1.3" />
            </svg>
          </button>
        </>
      )}
    </span>
  );
}
