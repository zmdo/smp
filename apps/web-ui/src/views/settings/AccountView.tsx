import QRCode from "qrcode";
import { FormEvent, useEffect, useState } from "react";
import { ApiError, api } from "../../api";
import { useAuth } from "../../auth";

export function AccountView() {
  const auth = useAuth();
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [setup, setSetup] = useState<{ secret: string; otpauth_uri: string } | null>(null);
  const [qrDataUrl, setQrDataUrl] = useState("");
  const [confirmCode, setConfirmCode] = useState("");
  const [disablePassword, setDisablePassword] = useState("");
  const [disableCode, setDisableCode] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [username, setUsername] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    void auth.refresh();
  }, []);

  async function saveUsername(event: FormEvent) {
    event.preventDefault();
    setError("");
    setMessage("");
    setBusy(true);
    try {
      await api("/api/auth/username", { method: "POST", body: JSON.stringify({ username }) });
      setMessage("用户名已修改");
      await auth.refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "修改失败");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (auth.username) setUsername(auth.username);
  }, [auth.username]);

  async function beginSetup() {
    setError("");
    setMessage("");
    setBusy(true);
    try {
      const created = await api<{ secret: string; otpauth_uri: string }>("/api/auth/totp/setup", { method: "POST" });
      setQrDataUrl(await QRCode.toDataURL(created.otpauth_uri, { margin: 1, width: 196 }));
      setSetup(created);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "无法开始设置");
    } finally {
      setBusy(false);
    }
  }

  async function confirmSetup(event: FormEvent) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      await api("/api/auth/totp/confirm", { method: "POST", body: JSON.stringify({ code: confirmCode }) });
      setSetup(null);
      setQrDataUrl("");
      setConfirmCode("");
      setMessage("两步验证已开启");
      await auth.refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "确认失败");
    } finally {
      setBusy(false);
    }
  }

  async function disable(event: FormEvent) {
    event.preventDefault();
    setError("");
    setMessage("");
    setBusy(true);
    try {
      await api("/api/auth/totp/disable", { method: "POST", body: JSON.stringify({ password: disablePassword, code: disableCode }) });
      setDisablePassword("");
      setDisableCode("");
      setMessage("两步验证已关闭");
      await auth.refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "关闭失败");
    } finally {
      setBusy(false);
    }
  }

  async function changePassword(event: FormEvent) {
    event.preventDefault();
    setError("");
    setMessage("");
    setBusy(true);
    try {
      await api("/api/auth/password", { method: "POST", body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }) });
      setCurrentPassword("");
      setNewPassword("");
      setMessage("密码已修改");
      await auth.refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "修改失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      {error && <p className="banner error">{error}</p>}
      {message && <p className="banner ok">{message}</p>}
      <section className="panel">
        <header className="panel-head"><h1><i className="mark" />登录安全</h1></header>
        <div className="panel-body">
          <form className="panel-form" onSubmit={saveUsername}>
            <label>用户名<input value={username} autoComplete="username" required onChange={(event) => setUsername(event.target.value)} /></label>
            <button className="primary" type="submit" disabled={busy}>保存用户名</button>
          </form>
          <p>两步验证：<strong>{auth.totpEnabled ? "已开启" : "未开启"}</strong></p>
          {!auth.totpEnabled ? (
            !setup ? (
              <button className="primary" type="button" disabled={busy} onClick={() => void beginSetup()}>开启两步验证</button>
            ) : (
              <form className="panel-form" onSubmit={confirmSetup}>
                <p className="muted">用验证器扫描二维码，或手动添加下面的密钥，再填写它给出的 6 位验证码。确认后才会真正开启。</p>
                <img className="qr" src={qrDataUrl} width={196} height={196} alt="两步验证二维码" />
                <p className="mono">{setup.secret}</p>
                <label>验证码<input value={confirmCode} inputMode="numeric" maxLength={6} required onChange={(event) => setConfirmCode(event.target.value)} /></label>
                <div className="row">
                  <button className="primary" type="submit" disabled={busy}>确认开启</button>
                  <button className="link" type="button" onClick={() => { setSetup(null); setQrDataUrl(""); }}>取消</button>
                </div>
              </form>
            )
          ) : (
            <form className="panel-form" onSubmit={disable}>
              <label>密码<input value={disablePassword} type="password" autoComplete="current-password" required onChange={(event) => setDisablePassword(event.target.value)} /></label>
              <label>验证码<input value={disableCode} inputMode="numeric" maxLength={6} required onChange={(event) => setDisableCode(event.target.value)} /></label>
              <button className="primary" type="submit" disabled={busy}>关闭两步验证</button>
            </form>
          )}
        </div>
      </section>
      <section className="panel">
        <header className="panel-head"><h1><i className="mark" />修改密码</h1></header>
        <div className="panel-body">
          <form className="panel-form" onSubmit={changePassword}>
            <label>当前密码<input value={currentPassword} type="password" autoComplete="current-password" required onChange={(event) => setCurrentPassword(event.target.value)} /></label>
            <label>新密码<input value={newPassword} type="password" autoComplete="new-password" required onChange={(event) => setNewPassword(event.target.value)} /></label>
            <button className="primary" type="submit" disabled={busy}>保存</button>
          </form>
        </div>
      </section>
    </>
  );
}
