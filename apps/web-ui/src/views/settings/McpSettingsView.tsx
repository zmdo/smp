import { FormEvent, useEffect, useMemo, useState } from "react";
import { ApiError, api } from "../../api";

interface McpSettings {
  enabled: boolean;
  has_token: boolean;
  token_last4: string | null;
  expose_servers: boolean;
  expose_wallets: boolean;
  expose_cards: boolean;
}

export function McpSettingsView() {
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [enabled, setEnabled] = useState(false);
  const [hasToken, setHasToken] = useState(false);
  const [tokenLast4, setTokenLast4] = useState<string | null>(null);
  const [exposeServers, setExposeServers] = useState(true);
  const [exposeWallets, setExposeWallets] = useState(true);
  const [exposeCards, setExposeCards] = useState(true);
  const [freshToken, setFreshToken] = useState("");
  const endpoint = `${window.location.origin}/mcp`;
  const snippet = useMemo(() => JSON.stringify({
    mcpServers: {
      策略控制台: { url: endpoint, headers: { Authorization: `Bearer ${freshToken || "在这里粘贴令牌"}` } },
    },
  }, null, 2), [endpoint, freshToken]);

  function apply(settings: McpSettings) {
    setEnabled(settings.enabled);
    setHasToken(settings.has_token);
    setTokenLast4(settings.token_last4);
    setExposeServers(settings.expose_servers);
    setExposeWallets(settings.expose_wallets);
    setExposeCards(settings.expose_cards);
  }

  useEffect(() => {
    api<McpSettings>("/api/mcp").then(apply).catch((err) => setError(err instanceof ApiError ? err.message : "加载失败"));
  }, []);

  async function save(event: FormEvent) {
    event.preventDefault();
    setError("");
    setMessage("");
    setBusy(true);
    try {
      apply(await api<McpSettings>("/api/mcp", {
        method: "POST",
        body: JSON.stringify({ enabled, expose_servers: exposeServers, expose_wallets: exposeWallets, expose_cards: exposeCards }),
      }));
      setMessage("已保存");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "保存失败");
    } finally {
      setBusy(false);
    }
  }

  async function rotate() {
    if (hasToken && !window.confirm("重置后，原来的令牌会立即失效。")) return;
    setError("");
    setMessage("");
    setBusy(true);
    try {
      const created = await api<{ token: string; token_last4: string }>("/api/mcp/token", { method: "POST" });
      setFreshToken(created.token);
      setHasToken(true);
      setTokenLast4(created.token_last4);
      setMessage("新令牌只显示这一次，请马上复制。");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "无法生成令牌");
    } finally {
      setBusy(false);
    }
  }

  async function copy(text: string) {
    setError("");
    try {
      await navigator.clipboard.writeText(text);
      setMessage("已复制");
    } catch {
      setError("复制失败");
    }
  }

  return (
    <>
      {error && <p className="banner error">{error}</p>}
      {message && <p className="banner ok">{message}</p>}
      <section className="panel">
        <header className="panel-head"><h1><i className="mark" />MCP</h1></header>
        <div className="panel-body">
          <p className="muted">控制台提供一个只读 MCP 接口。客户端用下面的地址和令牌连接后，只能读取勾选的内容，不会拿到卡号、安全码、助记词或 SSH 私钥。</p>
          <form className="panel-form" onSubmit={save}>
            <label className="check"><input checked={enabled} type="checkbox" onChange={(event) => setEnabled(event.target.checked)} />开启 MCP</label>
            <label className="check"><input checked={exposeServers} type="checkbox" onChange={(event) => setExposeServers(event.target.checked)} />服务器和容器</label>
            <label className="check"><input checked={exposeWallets} type="checkbox" onChange={(event) => setExposeWallets(event.target.checked)} />钱包地址</label>
            <label className="check"><input checked={exposeCards} type="checkbox" onChange={(event) => setExposeCards(event.target.checked)} />虚拟信用卡摘要（只有尾号）</label>
            <button className="primary" type="submit" disabled={busy}>保存</button>
          </form>
        </div>
      </section>
      <section className="panel">
        <header className="panel-head"><h1><i className="mark" />连接信息</h1></header>
        <div className="panel-body">
          <p>端点</p>
          <p className="mono">{endpoint}</p>
          <p>令牌 {hasToken ? `已设置，尾号 ${tokenLast4}` : "尚未生成"}</p>
          {freshToken && <p className="mono">{freshToken}</p>}
          <div className="row">
            <button className="primary" type="button" disabled={busy} onClick={() => void rotate()}>{hasToken ? "重置令牌" : "生成令牌"}</button>
            {freshToken && <button className="link" type="button" onClick={() => void copy(freshToken)}>复制令牌</button>}
            <button className="link" type="button" onClick={() => void copy(endpoint)}>复制端点</button>
          </div>
          <p className="sub">把下面这段放进客户端的 MCP 配置。令牌重置后，旧配置会失效。</p>
          <pre className="config">{snippet}</pre>
        </div>
      </section>
    </>
  );
}
