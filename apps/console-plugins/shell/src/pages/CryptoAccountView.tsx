import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate } from "../route";
import { ApiError, api, formatTime } from "../api";

interface WalletRow {
  id: string;
  name: string;
  created_at: string;
}

interface Created {
  id: string;
  name: string;
  mnemonic?: string;
}

type Mode = "list" | "create" | "import" | "backup";

export function CryptoAccountView() {
  const navigate = useNavigate();
  const [wallets, setWallets] = useState<WalletRow[]>([]);
  const [error, setError] = useState("");
  const [mode, setMode] = useState<Mode>("list");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [mnemonic, setMnemonic] = useState("");
  const [createdMnemonic, setCreatedMnemonic] = useState("");
  const [createdId, setCreatedId] = useState("");
  const [saved, setSaved] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function load() {
    try {
      setWallets(await api<WalletRow[]>("/api/wallets"));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "加载失败");
    }
  }

  useEffect(() => { void load(); }, []);

  function resetForm() {
    setName("");
    setPassword("");
    setMnemonic("");
    setError("");
  }

  function open(next: "create" | "import") {
    resetForm();
    setCreatedMnemonic("");
    setCreatedId("");
    setMode(next);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const created = await api<Created>("/api/wallets", {
        method: "POST",
        body: JSON.stringify({ name, password, mnemonic: mode === "import" ? mnemonic : null }),
      });
      setPassword("");
      setMnemonic("");
      if (created.mnemonic) {
        setCreatedMnemonic(created.mnemonic);
        setCreatedId(created.id);
        setSaved(false);
        setMode("backup");
      } else {
        navigate(`/accounts/crypto/${created.id}`);
      }
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "保存失败");
    } finally {
      setSubmitting(false);
    }
  }

  function finishBackup() {
    const id = createdId;
    setCreatedMnemonic("");
    setCreatedId("");
    setSaved(false);
    setMode("list");
    if (id) navigate(`/accounts/crypto/${id}`);
  }

  const words = createdMnemonic.split(" ").filter(Boolean);

  return (
    <>
      {error && <p className="banner error">{error}</p>}
      {mode === "backup" ? (
        <section className="panel">
          <header className="panel-head"><h1><i className="mark" />抄写助记词</h1></header>
          <div className="panel-body">
            <p className="sub">这是唯一一次显示这组助记词。离开本页之后，页面不再保留它。</p>
            <ol className="mnemonic">
              {words.map((word, index) => <li key={index}><span>{index + 1}</span>{word}</li>)}
            </ol>
            <label className="check"><input type="checkbox" checked={saved} onChange={(event) => setSaved(event.target.checked)} />我已经把助记词抄写到离线的地方</label>
            <div className="row"><button className="primary" type="button" disabled={!saved} onClick={finishBackup}>完成</button></div>
          </div>
        </section>
      ) : (mode === "create" || mode === "import") && (
        <section className="panel">
          <header className="panel-head"><h1><i className="mark" />{mode === "create" ? "创建钱包" : "导入钱包"}</h1></header>
          <div className="panel-body">
            <form className="panel-form" onSubmit={submit}>
              <label>名称<input value={name} required maxLength={80} placeholder="例如 日常资金" onChange={(event) => setName(event.target.value)} /></label>
              {mode === "import" && (
                <label>助记词<textarea value={mnemonic} required rows={3} autoComplete="off" spellCheck={false} placeholder="12 或 24 个英文单词" onChange={(event) => setMnemonic(event.target.value)} /></label>
              )}
              <label>登录密码<input value={password} required type="password" autoComplete="current-password" onChange={(event) => setPassword(event.target.value)} /></label>
              <p className="sub">用当前登录密码加密助记词。密码不对就不会保存。</p>
              <div className="row">
                <button className="primary" type="submit" disabled={submitting}>{mode === "create" ? "创建" : "导入"}</button>
                <button className="link" type="button" onClick={() => setMode("list")}>取消</button>
              </div>
            </form>
          </div>
        </section>
      )}
      <section className="panel">
        <header className="panel-head">
          <h1><i className="mark" />钱包实例 <em className="count">{wallets.length}</em></h1>
          <div className="tools">
            <button className="primary" type="button" onClick={() => open("create")}>创建钱包</button>
            <button className="link" type="button" onClick={() => open("import")}>导入钱包</button>
          </div>
        </header>
        {wallets.length === 0 ? <p className="empty">还没有钱包实例。可以创建新钱包，或用助记词导入。</p> : (
          <div className="table-wrap">
            <table className="clickable">
              <thead><tr><th>名称</th><th>创建时间</th></tr></thead>
              <tbody>
                {wallets.map((item) => (
                  <tr key={item.id} onClick={() => navigate(`/accounts/crypto/${item.id}`)}>
                    <td><Link className="op" to={`/accounts/crypto/${item.id}`} onClick={(event) => event.stopPropagation()}>{item.name}</Link></td>
                    <td>{formatTime(item.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <footer className="panel-foot">共 {wallets.length} 条</footer>
      </section>
    </>
  );
}
