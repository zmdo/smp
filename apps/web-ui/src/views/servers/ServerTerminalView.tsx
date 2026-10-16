import { FitAddon } from "@xterm/addon-fit";
import { Terminal } from "@xterm/xterm";
import "@xterm/xterm/css/xterm.css";
import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, type ServerSummary } from "../../api";

export function ServerTerminalView() {
  const { id = "" } = useParams();
  const host = useRef<HTMLDivElement>(null);
  const [title, setTitle] = useState("终端");
  const [error, setError] = useState("");

  useEffect(() => {
    let disposed = false;
    let term: Terminal | null = null;
    let socket: WebSocket | null = null;
    let fit: FitAddon | null = null;
    const element = host.current;
    if (!element) return;

    api<ServerSummary>(`/api/servers/${id}`).then((server) => {
      if (!disposed) setTitle(`${server.name} · ${server.ssh_user}@${server.intranet_host}`);
    }).catch(() => {
      if (!disposed) setTitle("终端");
    });

    term = new Terminal({
      cursorBlink: true,
      fontFamily: "Consolas, Cascadia Mono, monospace",
      fontSize: 13,
      theme: { background: "#1e1e1e", foreground: "#e8eaed", cursor: "#e8eaed" },
    });
    fit = new FitAddon();
    term.loadAddon(fit);
    term.open(element);
    fit.fit();
    const protocol = location.protocol === "https:" ? "wss" : "ws";
    socket = new WebSocket(`${protocol}://${location.host}/console-api/servers/${id}/terminal`);
    socket.binaryType = "arraybuffer";
    const sendSize = () => fit?.fit();
    socket.onopen = () => sendSize();
    socket.onmessage = (event) => {
      if (!term) return;
      if (typeof event.data === "string") term.write(event.data);
      else term.write(new Uint8Array(event.data));
    };
    socket.onclose = () => { if (!disposed) setError((current) => current || "终端连接已断开。"); };
    socket.onerror = () => setError("无法打开终端。");
    term.onData((data) => { if (socket?.readyState === WebSocket.OPEN) socket.send(new TextEncoder().encode(data)); });
    term.onResize(({ cols, rows }) => {
      if (socket?.readyState === WebSocket.OPEN) socket.send(JSON.stringify({ type: "resize", cols, rows }));
    });
    window.addEventListener("resize", sendSize);
    term.focus();
    return () => {
      disposed = true;
      window.removeEventListener("resize", sendSize);
      socket?.close();
      term?.dispose();
    };
  }, [id]);

  return (
    <section className="terminal-page">
      <header className="panel-head">
        <h1><i className="mark" />{title}</h1>
        <Link className="link" to={`/servers/${id}`}>返回</Link>
      </header>
      {error && <p className="banner error">{error}</p>}
      <div ref={host} className="terminal-host" />
    </section>
  );
}
