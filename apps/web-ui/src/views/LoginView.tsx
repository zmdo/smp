import { FormEvent, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { ApiError } from "../api";
import { useAuth } from "../auth";

export function LoginView() {
  const auth = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [totpCode, setTotpCode] = useState("");
  const [needTotp, setNeedTotp] = useState(false);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const result = await auth.login(username, password, needTotp ? totpCode : undefined);
      if (result.totp_required) {
        setNeedTotp(true);
        setError("这个账户开启了两步验证，请填写验证码");
        return;
      }
      if (result.ok) navigate(params.get("next") || "/servers", { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "登录失败");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="login-wrap">
      <form className="login-card" onSubmit={submit}>
        <div className="login-brand">
          <span className="logo-mark">策</span>
          <h1>策略控制台</h1>
        </div>
        <p className="muted">使用用户名和密码登录。开启两步验证后，还需要验证码。</p>
        {error && <p className="banner error">{error}</p>}
        <label>用户名<input value={username} autoComplete="username" required onChange={(event) => setUsername(event.target.value)} /></label>
        <label>密码<input value={password} type="password" autoComplete="current-password" required onChange={(event) => setPassword(event.target.value)} /></label>
        {needTotp && <label>验证码<input value={totpCode} inputMode="numeric" autoComplete="one-time-code" maxLength={6} required onChange={(event) => setTotpCode(event.target.value)} /></label>}
        <button className="primary" type="submit" disabled={submitting}>登录</button>
      </form>
    </div>
  );
}
