import { FormEvent, useEffect, useState } from "react";
import { ApiError, api, formatTime } from "../../api";

interface Wallet {
  id: string;
  name: string;
  address: string;
  created_at: string;
}

export function CryptoAccountView() {
  const [wallets, setWallets] = useState<Wallet[]>([]);
  const [error, setError] = useState("");
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState("create");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [mnemonic, setMnemonic] = useState("");
  const [creating, setCreating] = useState(false);
  const [created, setCreated] = useState<{ wallet: Wallet; mnemonic: string | null } | null>(null);
  const [backedUp, setBackedUp] = useState(false);

  async function load() {
    setError("");
    try {
      setWallets(await api<Wallet[]>("/api/wallets"));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "账户加载失败");
    }
  }

  useEffect(() => { void load(); }, []);

  function startCreate() {
    setOpen(true);
    setMode("create");
    setName("");
    setPassword("");
    setMnemonic("");
    setCreated(null);
    setBackedUp(false);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setCreating(true);
    try {
      const result = await api<{ wallet: Wallet; mnemonic: string | null }>("/api/wallets", {
        method: "POST",
        body: JSON.stringify({ name: name.trim(), password, mnemonic: mode === "import" ? mnemonic.trim() : null }),
      });
      setCreated(result);
      if (!result.mnemonic) {
        setOpen(false);
        window.location.assign(`/accounts/crypto/${result.wallet.id}`);
      }
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "创建失败");
    } finally {
      setCreating(false);
    }
  }

  function finish() {
    if (!created) return;
    const id = created.wallet.id;
    setCreated(null);
    setOpen(false);
    window.location.assign(`/accounts/crypto/${id}`);
  }

  return (
    <section>
      <div className="page-head">
        <div><h1>数字货币账户</h1><p className="muted">只在这台控制机上保存加密后的助记词。</p></div>
        <button className="primary" type="button" onClick={startCreate}>新建账户</button>
      </div>
      {error && <p className="banner error">{error}</p>}
      {wallets.length === 0 ? <section className="panel"><p className="muted">还没有账户。</p></section> : (
        <div className="table-wrap"><table>
          <thead><tr><th>名称</th><th>地址</th><th>创建时间</th></tr></thead>
          <tbody>
            {wallets.map((wallet) => (
              <tr key={wallet.id} className="clickable" onClick={() => { window.location.assign(`/accounts/crypto/${wallet.id}`); }}>
                <td>{wallet.name}</td>
                <td className="mono">{wallet.address}</td>
                <td>{formatTime(wallet.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table></div>
      )}
      {open && (
        <div className="modal-mask" onClick={() => { if (!created) setOpen(false); }}>
          <form className="modal" onSubmit={submit} onClick={(event) => event.stopPropagation()}>
            {!created ? (
              <>
                <h2>{mode === "create" ? "新建账户" : "导入账户"}</h2>
                <div className="mode-switch">
                  <button type="button" className={mode === "create" ? "active" : ""} onClick={() => setMode("create")}>新建</button>
                  <button type="button" className={mode === "import" ? "active" : ""} onClick={() => setMode("import")}>导入</button>
                </div>
                <label>名称<input value={name} maxLength={80} onChange={(event) => setName(event.target.value)} /></label>
                <label>加密密码<input value={password} type="password" autoComplete="new-password" onChange={(event) => setPassword(event.target.value)} /></label>
                {mode === "import" && <label>助记词<textarea value={mnemonic} rows={3} placeholder="12 或 24 个英文单词" onChange={(event) => setMnemonic(event.target.value)} /></label>}
                <div className="form-actions">
                  <button className="secondary" type="button" onClick={() => setOpen(false)}>取消</button>
                  <button className="primary" type="submit" disabled={creating}>{mode === "create" ? "创建" : "导入"}</button>
                </div>
              </>
            ) : (
              <>
                <h2>请抄下助记词</h2>
                <p className="muted">这是唯一一次显示。丢失后无法恢复这个账户。</p>
                <pre className="mnemonic">{created.mnemonic}</pre>
                <label className="check"><input type="checkbox" checked={backedUp} onChange={(event) => setBackedUp(event.target.checked)} />我已经抄好</label>
                <div className="form-actions"><button className="primary" type="button" disabled={!backedUp} onClick={finish}>完成</button></div>
              </>
            )}
          </form>
        </div>
      )}
    </section>
  );
}
