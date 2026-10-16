import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ApiError, api, formatTime, reachabilityLabel, type ServerGroup, type ServerSummary } from "../../api";
import { CopyButton } from "../../components/CopyButton";
import { NameEditor } from "../../components/NameEditor";
import { StatusPill } from "../../components/StatusPill";
import { UsageMeter } from "../../components/UsageMeter";
import { byteCaption, percentOf } from "../../usage";

export function ServerListView() {
  const navigate = useNavigate();
  const [servers, setServers] = useState<ServerSummary[]>([]);
  const [groups, setGroups] = useState<ServerGroup[]>([]);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [groupName, setGroupName] = useState("");
  const [creatingGroup, setCreatingGroup] = useState(false);

  async function refresh() {
    try {
      const [serverRows, groupRows] = await Promise.all([
        api<ServerSummary[]>("/api/servers"),
        api<ServerGroup[]>("/api/server-groups"),
      ]);
      setServers(serverRows);
      setGroups(groupRows);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "加载失败");
    }
  }

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), 1000);
    return () => window.clearInterval(timer);
  }, []);

  const sections = useMemo(() => {
    const text = query.trim().toLowerCase();
    const matched = text
      ? servers.filter((server) => `${server.name} ${server.intranet_host} ${server.ssh_user} ${server.region || ""} ${server.group_name || ""}`.toLowerCase().includes(text))
      : servers;
    const named = groups.map((group) => ({ id: group.id, name: group.name, servers: matched.filter((server) => server.group_id === group.id) }));
    const known = new Set(groups.map((group) => group.id));
    const loose = matched.filter((server) => !server.group_id || !known.has(server.group_id));
    const visibleGroups = text ? named.filter((section) => section.servers.length > 0) : named;
    if (loose.length > 0 || visibleGroups.length === 0) visibleGroups.push({ id: "", name: "未分组", servers: loose });
    return visibleGroups;
  }, [servers, groups, query]);
  const shownCount = sections.reduce((total, section) => total + section.servers.length, 0);

  async function createGroup(event: FormEvent) {
    event.preventDefault();
    setError("");
    const name = groupName.trim();
    if (!name) { setError("请填写分组名称"); return; }
    setCreatingGroup(true);
    try {
      await api<ServerGroup>("/api/server-groups", { method: "POST", body: JSON.stringify({ name }) });
      setGroupName("");
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "创建分组失败");
    } finally {
      setCreatingGroup(false);
    }
  }

  async function removeGroup(id: string) {
    setError("");
    try {
      await api(`/api/server-groups/${id}`, { method: "DELETE" });
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "删除分组失败");
    }
  }

  async function moveServer(server: ServerSummary, value: string) {
    setError("");
    try {
      await api(`/api/servers/${server.id}`, { method: "PATCH", body: JSON.stringify({ group_id: value || null }) });
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "调整分组失败");
      await refresh();
    }
  }

  return (
    <>
      {error && <p className="banner error">{error}</p>}
      <section className="panel">
        <header className="panel-head">
          <h1><i className="mark" />服务器实例 <em className="count">{shownCount}</em></h1>
          <div className="tools">
            <form className="group-create" onSubmit={createGroup}>
              <input value={groupName} maxLength={80} placeholder="新分组名称" onChange={(event) => setGroupName(event.target.value)} />
              <button className="secondary" type="submit" disabled={creatingGroup}>新建分组</button>
            </form>
            <input value={query} className="search" type="search" placeholder="搜索" onChange={(event) => setQuery(event.target.value)} />
            <Link className="icon" to="/servers/new" title="登记服务器">+</Link>
          </div>
        </header>
        {servers.length === 0 && groups.length === 0 ? <div className="empty">还没有服务器。点右上角登记一台机器。</div> : shownCount === 0 && query.trim() ? <div className="empty">没有匹配的服务器。</div> : (
          <div className="table-wrap">
            <table className="clickable">
              <thead>
                <tr>
                  <th>名称</th><th>地址</th><th className="nowrap">区域</th><th>状态</th><th>CPU</th><th>内存</th><th>硬盘</th><th>Docker</th><th>容器</th><th>最近检查</th><th>操作</th>
                </tr>
              </thead>
              <tbody>
                {sections.map((section) => (
                  <GroupRows key={section.id || "ungrouped"} section={section} groups={groups} onOpen={(serverId) => navigate(`/servers/${serverId}`)} onRemove={removeGroup} onMove={moveServer} onRename={(id, name) => { setServers((rows) => rows.map((row) => row.id === id ? { ...row, name } : row)); setError(""); }} onFailed={setError} />
                ))}
              </tbody>
            </table>
          </div>
        )}
        <footer className="panel-foot">共 {shownCount} 条</footer>
      </section>
    </>
  );
}

function GroupRows({ section, groups, onOpen, onRemove, onMove, onRename, onFailed }: {
  section: { id: string; name: string; servers: ServerSummary[] };
  groups: ServerGroup[];
  onOpen: (id: string) => void;
  onRemove: (id: string) => void;
  onMove: (server: ServerSummary, value: string) => void;
  onRename: (id: string, name: string) => void;
  onFailed: (message: string) => void;
}) {
  return (
    <>
      <tr className="group-head">
        <td colSpan={11}>
          <strong>{section.name}</strong>
          <em className="count">{section.servers.length}</em>
          {section.id && <button className="link" type="button" onClick={() => onRemove(section.id)}>删除分组</button>}
        </td>
      </tr>
      {section.servers.length === 0 && <tr className="group-empty"><td colSpan={11}>这个分组还没有服务器。</td></tr>}
      {section.servers.map((server) => (
        <tr key={server.id} onClick={() => onOpen(server.id)}>
          <td><NameEditor id={server.id} name={server.name} onSaved={(name) => onRename(server.id, name)} onFailed={onFailed} /></td>
          <td className="mono nowrap"><span className="copy-line">{server.intranet_host}<CopyButton value={server.intranet_host} /></span></td>
          <td className="nowrap">{server.region || "—"}</td>
          <td><StatusPill value={server.reachability} label={reachabilityLabel[server.reachability] || server.reachability} /></td>
          <td><UsageMeter caption={server.cpu_cores ? `${server.cpu_cores} 核` : ""} percent={server.cpu_percent} /></td>
          <td><UsageMeter caption={byteCaption(server.mem_used_bytes, server.mem_total_bytes)} percent={percentOf(server.mem_used_bytes, server.mem_total_bytes)} /></td>
          <td><UsageMeter caption={byteCaption(server.disk_used_bytes, server.disk_total_bytes)} percent={percentOf(server.disk_used_bytes, server.disk_total_bytes)} /></td>
          <td>{server.docker_version || "—"}</td>
          <td>{server.container_count === null ? "—" : String(server.container_count)}</td>
          <td>{formatTime(server.last_checked_at)}</td>
          <td className="ops" onClick={(event) => event.stopPropagation()}>
            <select className="group-pick" value={server.group_id || ""} onChange={(event) => onMove(server, event.target.value)}>
              <option value="">未分组</option>
              {groups.map((group) => <option key={group.id} value={group.id}>{group.name}</option>)}
            </select>
            <Link className="op" to={`/servers/${server.id}`}>查看</Link>
            <Link className="op" to={`/servers/${server.id}/terminal`}>终端</Link>
          </td>
        </tr>
      ))}
    </>
  );
}
