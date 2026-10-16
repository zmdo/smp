import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "../route";
import { ApiError, api, type ComponentInfo, type ServerDetail, type ServerGroup, type SshKey } from "../api";

export function ServerFormView() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const isEdit = id !== "";
  const [name, setName] = useState("");
  const [intranetHost, setIntranetHost] = useState("");
  const [sshPort, setSshPort] = useState(22);
  const [sshUser, setSshUser] = useState("");
  const [authMethod, setAuthMethod] = useState<"private_key" | "password">("private_key");
  const [keySource, setKeySource] = useState<"existing" | "new">("new");
  const [keys, setKeys] = useState<SshKey[]>([]);
  const [selectedKeyId, setSelectedKeyId] = useState("");
  const [keyName, setKeyName] = useState("");
  const [secret, setSecret] = useState("");
  const [autoInstall, setAutoInstall] = useState(false);
  const [components, setComponents] = useState<ComponentInfo[]>([]);
  const [selectedComponents, setSelectedComponents] = useState<string[]>([]);
  const [groups, setGroups] = useState<ServerGroup[]>([]);
  const [groupId, setGroupId] = useState("");
  const [region, setRegion] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testedSignature, setTestedSignature] = useState("");

  const connectionSignature = useMemo(() => JSON.stringify({
    host: intranetHost.trim(), port: Number(sshPort), user: sshUser.trim(), auth: authMethod,
    keySource, keyId: selectedKeyId, secret,
  }), [intranetHost, sshPort, sshUser, authMethod, keySource, selectedKeyId, secret]);
  const canSave = isEdit || (testedSignature !== "" && testedSignature === connectionSignature);

  useEffect(() => {
    setTestedSignature("");
    setNotice("");
  }, [connectionSignature]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [keyRows, componentRows, groupRows] = await Promise.all([
          api<SshKey[]>("/api/ssh-keys"),
          api<ComponentInfo[]>("/api/components"),
          api<ServerGroup[]>("/api/server-groups"),
        ]);
        if (cancelled) return;
        setKeys(keyRows);
        setComponents(componentRows);
        setGroups(groupRows);
        if (!isEdit) {
          setKeySource(keyRows.length ? "existing" : "new");
          setSelectedKeyId(keyRows[0]?.id || "");
          return;
        }
        const server = await api<ServerDetail>(`/api/servers/${id}`);
        if (cancelled) return;
        setName(server.name);
        setIntranetHost(server.intranet_host);
        setSshPort(server.ssh_port);
        setSshUser(server.ssh_user);
        setAuthMethod(server.auth_method);
        if (server.ssh_key_id) {
          setKeySource("existing");
          setSelectedKeyId(server.ssh_key_id);
        }
        setAutoInstall(server.auto_install);
        setGroupId(server.group_id || "");
        setRegion(server.region || "");
        setSelectedComponents(server.component_ids.length ? [...server.component_ids] : componentRows.map((item) => item.id));
      } catch (err) {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "加载失败");
      }
    })();
    return () => { cancelled = true; };
  }, [id, isEdit]);

  function authProblem(): string {
    if (!intranetHost.trim() || !sshUser.trim()) return "请填写地址和 SSH 用户";
    if (authMethod === "password") return secret.trim() ? "" : "请填写口令";
    if (keySource === "existing") return selectedKeyId ? "" : "请选择一把密钥";
    return secret.trim() ? "" : "请粘贴私钥";
  }

  function connectionBody(): Record<string, unknown> {
    const body: Record<string, unknown> = {
      intranet_host: intranetHost, ssh_port: Number(sshPort), ssh_user: sshUser, auth_method: authMethod,
    };
    if (authMethod === "password" || keySource === "new") body.secret = secret;
    else body.ssh_key_id = selectedKeyId;
    return body;
  }

  async function testConnection() {
    setError("");
    setNotice("");
    const problem = authProblem();
    if (problem) { setError(problem); setTestedSignature(""); return; }
    const signature = connectionSignature;
    setTesting(true);
    setTestedSignature("");
    try {
      const result = await api<{ ok: boolean; message: string }>("/api/servers/test-connection", { method: "POST", body: JSON.stringify(connectionBody()) });
      if (connectionSignature !== signature) return;
      if (result.ok) { setTestedSignature(signature); setNotice(result.message); }
      else setError(result.message);
    } catch (err) {
      if (connectionSignature === signature) setError(err instanceof ApiError ? err.message : "连接测试失败");
    } finally {
      setTesting(false);
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    if (!isEdit && !canSave) { setError("请先测试连接"); return; }
    if (authMethod === "password") {
      if (!isEdit && !secret.trim()) { setError("请填写口令"); return; }
    } else if (keySource === "existing") {
      if (!selectedKeyId) { setError("请选择一把密钥"); return; }
    } else if (!isEdit && !secret.trim()) {
      setError("请粘贴私钥"); return;
    } else if (secret.trim() && !keyName.trim()) {
      setError("请填写密钥名称，保存后会出现在服务器密钥里"); return;
    }
    setSubmitting(true);
    const body: Record<string, unknown> = { name, ssh_port: Number(sshPort), ssh_user: sshUser, auth_method: authMethod };
    if (!isEdit) body.intranet_host = intranetHost;
    if (authMethod === "password") { if (secret) body.secret = secret; }
    else if (keySource === "existing") body.ssh_key_id = selectedKeyId;
    else if (secret.trim()) { body.secret = secret; body.ssh_key_name = keyName; }
    body.group_id = groupId || null;
    body.region = region.trim();
    if (!isEdit) {
      body.auto_install = autoInstall;
      body.component_ids = autoInstall ? selectedComponents : [];
      if (autoInstall && selectedComponents.length === 0) { setError("请选择要安装的组件"); setSubmitting(false); return; }
    }
    try {
      const result = await api<{ server: { id: string }; job: { id: string } | null }>(isEdit ? `/api/servers/${id}` : "/api/servers", {
        method: isEdit ? "PATCH" : "POST", body: JSON.stringify(body),
      });
      navigate(result.job ? `/servers/${result.server.id}?job=${result.job.id}` : `/servers/${result.server.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "保存失败");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="panel">
      <header className="panel-head"><h1><i className="mark" />{isEdit ? "编辑服务器" : "登记服务器"}</h1></header>
      <div className="panel-body">
        <p className="muted" style={{ marginTop: 0 }}>{isEdit ? "地址登记后不能修改。区域、登录方式和分组仍可以调整。" : "填写这台机器的 IP，公网或内网都可以。区域留空时，内网记为内网，外网按 IP 自动查询。需要 Docker 时可以在下面勾选自动安装，也可以连上之后再装。"}</p>
        <form className="panel-form" onSubmit={submit}>
          {error && <p className="banner error">{error}</p>}
          {notice && <p className="banner ok">{notice}</p>}
          <label>名称<input value={name} required maxLength={80} onChange={(event) => setName(event.target.value)} /></label>
          <label>分组
            <select value={groupId} onChange={(event) => setGroupId(event.target.value)}>
              <option value="">未分组</option>
              {groups.map((group) => <option key={group.id} value={group.id}>{group.name}</option>)}
            </select>
          </label>
          <label>地址<input value={intranetHost} disabled={isEdit} required placeholder="例如 10.0.0.8" onChange={(event) => setIntranetHost(event.target.value)} /></label>
          <label>区域<input value={region} maxLength={80} placeholder="留空则自动判断，内网为内网" onChange={(event) => setRegion(event.target.value)} /></label>
          <label>SSH 端口<input value={sshPort} type="number" min={1} max={65535} required onChange={(event) => setSshPort(Number(event.target.value))} /></label>
          <label>SSH 用户<input value={sshUser} required maxLength={64} onChange={(event) => setSshUser(event.target.value)} /></label>
          <div className="choices">
            <label><input checked={authMethod === "private_key"} type="radio" name="auth" onChange={() => setAuthMethod("private_key")} />密钥</label>
            <label><input checked={authMethod === "password"} type="radio" name="auth" onChange={() => setAuthMethod("password")} />口令</label>
          </div>
          {authMethod === "private_key" ? (
            <>
              <div className="choices">
                <label><input checked={keySource === "existing"} type="radio" name="key-source" disabled={keys.length === 0} onChange={() => setKeySource("existing")} />已有密钥</label>
                <label><input checked={keySource === "new"} type="radio" name="key-source" onChange={() => setKeySource("new")} />填写密钥</label>
              </div>
              {keySource === "existing" ? (
                <label>密钥
                  <select value={selectedKeyId} required onChange={(event) => setSelectedKeyId(event.target.value)}>
                    {keys.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                  </select>
                </label>
              ) : (
                <>
                  <label>密钥名称<input value={keyName} maxLength={80} placeholder="例如 机房跳板" onChange={(event) => setKeyName(event.target.value)} /></label>
                  <label>私钥<textarea value={secret} className="mono" spellCheck={false} placeholder={isEdit ? "留空则不修改当前密钥" : "粘贴 PEM 私钥"} onChange={(event) => setSecret(event.target.value)} /></label>
                  <p className="muted">新粘贴的私钥会自动加入服务器密钥。同一把私钥不会重复保存。</p>
                </>
              )}
            </>
          ) : (
            <label>口令<input value={secret} type="password" placeholder={isEdit ? "留空则不修改" : ""} onChange={(event) => setSecret(event.target.value)} /></label>
          )}
          {!isEdit && (
            <>
              <label className="check">
                <input checked={autoInstall} type="checkbox" onChange={(event) => {
                  const checked = event.target.checked;
                  setAutoInstall(checked);
                  if (checked && selectedComponents.length === 0) setSelectedComponents(components.map((item) => item.id));
                }} />
                自动安装必要组件
              </label>
              {autoInstall && (
                <div className="component-picks">
                  {components.map((item) => (
                    <label key={item.id}>
                      <input checked={selectedComponents.includes(item.id)} type="checkbox" onChange={(event) => {
                        setSelectedComponents((current) => event.target.checked ? [...current, item.id] : current.filter((value) => value !== item.id));
                      }} />
                      <span><strong>{item.name}</strong><span className="muted">{item.summary}</span></span>
                    </label>
                  ))}
                  {components.length === 0 && <p className="muted">没有可安装的组件。</p>}
                </div>
              )}
            </>
          )}
          <div className="row">
            {!isEdit && <button className="secondary" type="button" disabled={testing || submitting} onClick={() => void testConnection()}>{testing ? "测试中" : "测试连接"}</button>}
            <button className="primary" type="submit" disabled={submitting || testing || !canSave}>保存</button>
            <Link className="link" to={isEdit ? `/servers/${id}` : "/servers"}>取消</Link>
          </div>
          {!isEdit && <p className="muted">先测试连接，通过后才能保存。</p>}
        </form>
      </div>
    </section>
  );
}
