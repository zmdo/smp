import { FormEvent, useEffect, useMemo, useState } from "react";
import { ApiError, api, formatTime } from "../../api";

interface VenueField { key: string; label: string }
interface Venue { id: string; name: string; wallet: string; fields: VenueField[] }
interface Balance { asset: string; free: string; locked: string; total: string }
interface ExchangeAccount {
  id: string; name: string; venue: string; venue_name: string; wallet: string;
  balances: Balance[]; balance_error: string; checked_at: string | null; created_at: string;
}

export function ExchangeView() {
  const [venues, setVenues] = useState<Venue[]>([]);
  const [rows, setRows] = useState<ExchangeAccount[]>([]);
  const [error, setError] = useState("");
  const [creating, setCreating] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [refreshing, setRefreshing] = useState("");
  const [name, setName] = useState("");
  const [venueId, setVenueId] = useState("");
  const [credentials, setCredentials] = useState<Record<string, string>>({});
  const [selectedId, setSelectedId] = useState("");
  const venue = useMemo(() => venues.find((item) => item.id === venueId) || venues[0], [venues, venueId]);
  const selected = rows.find((item) => item.id === selectedId) || null;

  function resetCredentials(nextVenue = venue) {
    const next: Record<string, string> = {};
    for (const field of nextVenue?.fields || []) next[field.key] = "";
    setCredentials(next);
  }

  async function load(prefer?: string) {
    const accounts = await api<ExchangeAccount[]>("/api/exchanges");
    setRows(accounts);
    setSelectedId((current) => {
      const wanted = prefer ?? current;
      if (wanted && accounts.some((item) => item.id === wanted)) return wanted;
      return accounts[0]?.id || "";
    });
  }

  useEffect(() => {
    api<Venue[]>("/api/exchanges/venues").then(async (items) => {
      setVenues(items);
      const first = items[0];
      setVenueId(first?.id || "");
      const next: Record<string, string> = {};
      for (const field of first?.fields || []) next[field.key] = "";
      setCredentials(next);
      await load();
    }).catch((err) => setError(err instanceof ApiError ? err.message : "加载失败"));
  }, []);

  function summary(account: ExchangeAccount): string {
    if (account.balance_error && account.balances.length === 0) return "查询失败";
    if (!account.checked_at) return "尚未查询";
    if (account.balances.length === 0) return "没有余额";
    return account.balances.slice(0, 3).map((item) => `${item.asset} ${item.total}`).join("，");
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const created = await api<ExchangeAccount>("/api/exchanges", {
        method: "POST",
        body: JSON.stringify({ name, venue: venueId, credentials }),
      });
      setCreating(false);
      await load(created.id);
      if (created.balance_error) setError(created.balance_error);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "保存失败");
    } finally {
      setSubmitting(false);
    }
  }

  async function refresh(account: ExchangeAccount) {
    setError("");
    setRefreshing(account.id);
    try {
      const updated = await api<ExchangeAccount>(`/api/exchanges/${account.id}/refresh`, { method: "POST" });
      await load(updated.id);
      if (updated.balance_error) setError(updated.balance_error);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "查询余额失败");
    } finally {
      setRefreshing("");
    }
  }

  async function remove(account: ExchangeAccount) {
    if (!window.confirm(`删除交易所「${account.name}」？不会影响交易所里的资产。`)) return;
    setError("");
    try {
      await api(`/api/exchanges/${account.id}`, { method: "DELETE" });
      await load(selectedId === account.id ? "" : selectedId);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "删除失败");
    }
  }

  return (
    <>
      {error && <p className="banner error">{error}</p>}
      <section className="panel">
        <header className="panel-head">
          <h1><i className="mark" />交易所</h1>
          <div className="tools">
            <button className="icon" type="button" title="加入交易所" onClick={() => {
              setError(""); setName(""); const first = venues[0]?.id || ""; setVenueId(first);
              const next: Record<string, string> = {};
              for (const field of (venues.find((item) => item.id === first) || venues[0])?.fields || []) next[field.key] = "";
              setCredentials(next); setCreating(true);
            }}>+</button>
          </div>
        </header>
        <div className="panel-body">
          {creating && (
            <form className="panel-form" onSubmit={submit}>
              <p className="muted" style={{ marginTop: 0 }}>只读取余额，不会下单或提币。API 需要有读取权限，并把这台电脑的出口 IP 加到交易所白名单。</p>
              <label>名称<input value={name} required maxLength={80} placeholder="例如 币安主账户" onChange={(event) => setName(event.target.value)} /></label>
              <label>交易所
                <select value={venueId} onChange={(event) => { const id = event.target.value; setVenueId(id); resetCredentials(venues.find((item) => item.id === id)); }}>
                  {venues.map((item) => <option key={item.id} value={item.id}>{item.name}（{item.wallet}）</option>)}
                </select>
              </label>
              {(venue?.fields || []).map((field) => (
                <label key={field.key}>{field.label}
                  <input value={credentials[field.key] || ""} type="password" required autoComplete="off" onChange={(event) => setCredentials((current) => ({ ...current, [field.key]: event.target.value }))} />
                </label>
              ))}
              <div className="row">
                <button className="primary" type="submit" disabled={submitting}>{submitting ? "查询中" : "保存并查询余额"}</button>
                <button className="link" type="button" onClick={() => setCreating(false)}>取消</button>
              </div>
            </form>
          )}
          {!creating && rows.length === 0 && <p className="empty">还没有交易所。点右上角加入。</p>}
          {rows.length > 0 && (
            <div className="table-wrap">
              <table className="clickable">
                <thead><tr><th>名称</th><th>交易所</th><th>余额</th><th>最近查询</th><th>操作</th></tr></thead>
                <tbody>
                  {rows.map((account) => (
                    <tr key={account.id} onClick={() => setSelectedId(account.id)}>
                      <td>{account.name}</td>
                      <td>{account.venue_name}</td>
                      <td>{summary(account)}</td>
                      <td>{formatTime(account.checked_at)}</td>
                      <td className="ops" onClick={(event) => event.stopPropagation()}>
                        <button className="link" type="button" disabled={refreshing === account.id} onClick={() => void refresh(account)}>{refreshing === account.id ? "查询中" : "刷新余额"}</button>
                        <button className="link danger" type="button" onClick={() => void remove(account)}>删除</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>
      {selected && (
        <section className="panel">
          <header className="panel-head"><h2><i className="mark" />{selected.name} · {selected.venue_name} {selected.wallet}</h2></header>
          {selected.balance_error && <p className="banner error">{selected.balance_error}</p>}
          {selected.balances.length === 0 ? (
            <p className="empty">{selected.checked_at ? "没有非零余额。" : "还没有查询过余额。"}</p>
          ) : (
            <div className="table-wrap">
              <table>
                <thead><tr><th>币种</th><th>可用</th><th>冻结</th><th>合计</th></tr></thead>
                <tbody>
                  {selected.balances.map((item) => (
                    <tr key={item.asset}><td>{item.asset}</td><td className="mono">{item.free}</td><td className="mono">{item.locked}</td><td className="mono">{item.total}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}
    </>
  );
}
