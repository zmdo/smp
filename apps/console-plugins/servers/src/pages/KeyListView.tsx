import { FormEvent, useEffect, useMemo, useState } from "react";
import { ApiError, api, formatTime, type SshKey } from "../../../shared/src/api";

export function KeyListView() {
  const [keys, setKeys] = useState<SshKey[]>([]);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [secret, setSecret] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const visible = useMemo(() => {
    const text = query.trim().toLowerCase();
    if (!text) return keys;
    return keys.filter((item) => `${item.name} ${item.fingerprint}`.toLowerCase().includes(text));
  }, [keys, query]);

  async function load() {
    try {
      setKeys(await api<SshKey[]>("/api/ssh-keys"));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "加载失败");
    }
  }

  useEffect(() => { void load(); }, []);

  async function create(event: FormEvent) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await api("/api/ssh-keys", { method: "POST", body: JSON.stringify({ name, secret }) });
      setName("");
      setSecret("");
      setCreating(false);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "保存失败");
    } finally {
      setSubmitting(false);
    }
  }

  async function remove(item: SshKey) {
    if (!window.confirm(`删除密钥「${item.name}」？`)) return;
    setError("");
    try {
      await api(`/api/ssh-keys/${item.id}`, { method: "DELETE" });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "删除失败");
    }
  }

  return (
    <>
      {error && <p className="banner error">{error}</p>}
      {creating && (
        <section className="panel">
          <header className="panel-head"><h1><i className="mark" />添加密钥</h1></header>
          <div className="panel-body">
            <form className="panel-form" onSubmit={create}>
              <label>名称<input value={name} required maxLength={80} placeholder="例如 机房跳板" onChange={(event) => setName(event.target.value)} /></label>
              <label>私钥<textarea value={secret} className="mono" required spellCheck={false} placeholder="粘贴 PEM 私钥" onChange={(event) => setSecret(event.target.value)} /></label>
              <div className="row">
                <button className="primary" type="submit" disabled={submitting}>保存</button>
                <button className="link" type="button" onClick={() => setCreating(false)}>取消</button>
              </div>
            </form>
          </div>
        </section>
      )}
      <section className="panel">
        <header className="panel-head">
          <h1><i className="mark" />服务器密钥 <em className="count">{visible.length}</em></h1>
          <div className="tools">
            <input value={query} className="search" type="search" placeholder="搜索" onChange={(event) => setQuery(event.target.value)} />
            <button className="icon" type="button" title="添加密钥" onClick={() => setCreating(true)}>+</button>
          </div>
        </header>
        {visible.length === 0 ? (
          <div className="empty">{keys.length === 0 ? "还没有密钥。点右上角添加，或在登记服务器实例时粘贴一把新私钥。" : "没有匹配的密钥。"}</div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>名称</th><th>指纹</th><th>使用中</th><th>添加时间</th><th>操作</th></tr></thead>
              <tbody>
                {visible.map((item) => (
                  <tr key={item.id}>
                    <td>{item.name}</td>
                    <td className="mono">{item.fingerprint}</td>
                    <td>{item.server_count} 台服务器</td>
                    <td>{formatTime(item.created_at)}</td>
                    <td><button className="link danger" type="button" onClick={() => void remove(item)}>删除</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <footer className="panel-foot">共 {visible.length} 条</footer>
      </section>
    </>
  );
}
