import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import {
  ApiError, api, containerStatusLabel, formatTime, jobActionLabel, jobStatusLabel, reachabilityLabel, sleep,
  type ComponentInfo, type Job, type ServerDetail,
} from "../../api";
import { CopyButton } from "../../components/CopyButton";
import { NameEditor } from "../../components/NameEditor";
import { StatusPill } from "../../components/StatusPill";
import { UsageMeter } from "../../components/UsageMeter";
import { byteCaption, percentOf } from "../../usage";

export function ServerDetailView() {
  const { id = "" } = useParams();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [server, setServer] = useState<ServerDetail | null>(null);
  const [components, setComponents] = useState<ComponentInfo[]>([]);
  const [error, setError] = useState("");
  const [currentJob, setCurrentJob] = useState<Job | null>(null);
  const [busy, setBusy] = useState(false);
  const serverRef = useRef<ServerDetail | null>(null);
  const stopped = useRef(false);
  serverRef.current = server;

  async function load() {
    try {
      const next = await api<ServerDetail>(`/api/servers/${id}`);
      serverRef.current = next;
      setServer(next);
    } catch (err) {
      if (!serverRef.current) setError(err instanceof ApiError ? err.message : "加载失败");
    }
  }

  async function watchJob(jobId: string) {
    setBusy(true);
    try {
      let current = jobId;
      while (!stopped.current) {
        const job = await api<Job>(`/api/ops-jobs/${current}`);
        setCurrentJob(job);
        if (job.status === "succeeded" || job.status === "failed") {
          await load();
          const next = serverRef.current?.recent_jobs.find((item) => item.id !== job.id && (item.status === "queued" || item.status === "running"));
          if (next && !stopped.current) { current = next.id; continue; }
          return;
        }
        await sleep(1000);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "任务查询失败");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    stopped.current = false;
    let timer = 0;
    (async () => {
      try {
        setComponents(await api<ComponentInfo[]>("/api/components"));
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "组件列表加载失败");
      }
      await load();
      timer = window.setInterval(() => void load(), 1000);
      const requested = params.get("job") || "";
      const running = serverRef.current?.recent_jobs.find((job) => job.status === "queued" || job.status === "running");
      const jobId = requested || running?.id;
      if (jobId) await watchJob(jobId);
    })();
    return () => { stopped.current = true; window.clearInterval(timer); };
  }, [id]);

  const missingComponents = useMemo(
    () => components.filter((item) => server?.component_status[item.id]?.installed !== true),
    [components, server],
  );

  function componentState(componentId: string): string {
    const item = server?.component_status[componentId];
    if (!item) return "未检测";
    if (!item.installed) return "未安装";
    return item.detail ? `已安装 ${item.detail}` : "已安装";
  }

  async function run(action: "test" | "inspect") {
    setError("");
    try {
      const job = await api<Job>(`/api/servers/${id}/${action}`, { method: "POST" });
      await watchJob(job.id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "操作失败");
    }
  }

  async function installComponents() {
    setError("");
    try {
      const job = await api<Job>(`/api/servers/${id}/install-components`, { method: "POST" });
      await watchJob(job.id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "操作失败");
    }
  }

  async function remove() {
    if (!server) return;
    if (!window.confirm(`删除服务器「${server.name}」？这不会关闭那台机器上已经在跑的容器。`)) return;
    await api(`/api/servers/${id}`, { method: "DELETE" });
    navigate("/servers");
  }

  if (!server) return null;
  const showContainers = server.container_count !== null && server.reachability !== "docker_unavailable";
  return (
    <div>
      {error && <p className="banner error">{error}</p>}
      {currentJob && (
        <p className={`banner ${currentJob.status === "failed" ? "error" : currentJob.status === "succeeded" ? "ok" : ""}`}>
          {jobActionLabel[currentJob.action] || currentJob.action}：{jobStatusLabel[currentJob.status] || currentJob.status}
          {currentJob.output_excerpt ? `。${currentJob.output_excerpt}` : ""}
        </p>
      )}
      <section className="node-card">
        <div className="node-title">
          <NameEditor id={server.id} name={server.name} onSaved={(next) => { setServer({ ...server, name: next }); setError(""); }} onFailed={setError} />
          <StatusPill value={server.reachability} label={reachabilityLabel[server.reachability] || server.reachability} />
        </div>
        <p className="sub mono copy-line"><span>{server.intranet_host}</span><CopyButton value={server.intranet_host} /></p>
        <div className="usage-row">
          <div><span>CPU</span><UsageMeter caption={server.cpu_cores ? `${server.cpu_cores} 核` : ""} percent={server.cpu_percent} /></div>
          <div><span>内存</span><UsageMeter caption={byteCaption(server.mem_used_bytes, server.mem_total_bytes)} percent={percentOf(server.mem_used_bytes, server.mem_total_bytes)} /></div>
          <div><span>硬盘</span><UsageMeter caption={byteCaption(server.disk_used_bytes, server.disk_total_bytes)} percent={percentOf(server.disk_used_bytes, server.disk_total_bytes)} /></div>
        </div>
        <div className="node-grid">
          <div><span>区域</span>{server.region || "—"}</div>
          <div><span>SSH 用户</span>{server.ssh_user}</div>
          <div><span>端口</span>{server.ssh_port}</div>
          <div><span>分组</span>{server.group_name || "未分组"}</div>
          <div><span>登录</span>{server.auth_method === "private_key" ? (server.ssh_key_name || "密钥") : "口令"}</div>
          <div><span>Docker</span>{server.docker_version || "—"}</div>
          <div><span>Compose</span>{server.compose_version || "—"}</div>
          <div><span>容器</span>{server.container_count === null ? "—" : server.container_count}</div>
          <div><span>最近检查</span>{formatTime(server.last_checked_at)}</div>
          <div><span>主机指纹</span><span className="mono">{server.host_key_fingerprint || "测试连接后记录"}</span></div>
        </div>
        <div className="node-actions">
          <button className="link" type="button" disabled={busy} onClick={() => void run("test")}>测试连接</button>
          <button className="link" type="button" disabled={busy} onClick={() => void run("inspect")}>立即刷新</button>
          <Link className="link" to={`/servers/${server.id}/edit`}>编辑</Link>
          <button className="link danger" type="button" disabled={busy} onClick={() => void remove()}>删除</button>
        </div>
      </section>
      <section className="panel">
        <header className="panel-head">
          <h2><i className="mark" />必要组件</h2>
          {missingComponents.length > 0 && <button className="primary" type="button" disabled={busy} onClick={() => void installComponents()}>安装必要组件</button>}
        </header>
        {components.length === 0 ? <div className="empty">没有可安装的组件。</div> : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>组件</th><th>状态</th><th>说明</th></tr></thead>
              <tbody>
                {components.map((item) => (
                  <tr key={item.id}><td>{item.name}</td><td>{componentState(item.id)}</td><td className="muted">{item.summary}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {missingComponents.length > 0 && <footer className="panel-foot">只会安装还没有的组件，已经存在的会跳过。</footer>}
      </section>
      <section className="panel">
        <header className="panel-head"><h2><i className="mark" />容器 <em className="count">{server.containers.length}</em></h2></header>
        {server.reachability === "unknown" ? <div className="empty">尚未测试连接。</div>
          : server.reachability === "docker_unavailable" ? <div className="empty">Docker 还没装好。可以在上面一键安装必要组件。</div>
          : !showContainers ? <div className="empty">还没有成功的巡检。在线后会每 30 秒自动刷新，也可以现在立即刷新。</div>
          : server.containers.length === 0 ? <div className="empty">这台服务器上没有容器。</div>
          : (
            <div className="table-wrap">
              <table>
                <thead><tr><th>名称</th><th>镜像</th><th>状态</th><th>端口</th><th>来源</th></tr></thead>
                <tbody>
                  {server.containers.map((item) => (
                    <tr key={item.container_id}>
                      <td className="mono">{item.name}</td>
                      <td className="mono">{item.image}</td>
                      <td><StatusPill value={item.status} label={containerStatusLabel[item.status] || item.status} /></td>
                      <td className="mono">{item.ports || "—"}</td>
                      <td>{item.managed ? `本平台${item.strategy_slug ? " / " + item.strategy_slug : ""}` : "其他"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        {server.containers.length > 0 && <footer className="panel-foot">巡检时间 {formatTime(server.containers[0].observed_at)}</footer>}
      </section>
      <section className="panel">
        <header className="panel-head"><h2><i className="mark" />最近任务 <em className="count">{server.recent_jobs.length}</em></h2></header>
        {server.recent_jobs.length === 0 ? <div className="empty">还没有任务。</div> : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>动作</th><th>状态</th><th>时间</th><th>输出</th></tr></thead>
              <tbody>
                {server.recent_jobs.map((job) => (
                  <tr key={job.id}>
                    <td>{jobActionLabel[job.action] || job.action}</td>
                    <td><StatusPill value={job.status} label={jobStatusLabel[job.status] || job.status} /></td>
                    <td>{formatTime(job.finished_at || job.created_at)}</td>
                    <td>{job.output_excerpt || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
