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
      const result = await auth.login(username.trim(), password, totpCode.trim());
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
    <main className="login">
      <form className="login-card" onSubmit={submit}>
        <p className="eyebrow">策略控制台</p>
        <h1>登录</h1>
        <label>用户名<input value={username} autoComplete="username" onChange={(event) => setUsername(event.target.value)} /></label>
        <label>密码<input value={password} type="password" autoComplete="current-password" onChange={(event) => setPassword(event.target.value)} /></label>
        {needTotp && <label>验证码<input value={totpCode} inputMode="numeric" autoComplete="one-time-code" placeholder="6 位验证码" onChange={(event) => setTotpCode(event.target.value)} /></label>}
        {error && <p className="form-error">{error}</p>}
        <button className="primary" type="submit" disabled={submitting}>登录</button>
      </form>
    </main>
  );
}
