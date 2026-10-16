import { useState } from "react";
import { Link, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "./auth";
import { CardAccountView } from "./views/accounts/CardAccountView";
import { CryptoAccountView } from "./views/accounts/CryptoAccountView";
import { WalletDetailView } from "./views/accounts/WalletDetailView";
import { LoginView } from "./views/LoginView";
import { DashboardView } from "./views/DashboardView";
import { ExchangeView } from "./views/quant/ExchangeView";
import { MarketView } from "./views/quant/MarketView";
import { QuantOverviewView } from "./views/quant/QuantOverviewView";
import { QuantStrategyView } from "./views/quant/QuantStrategyView";
import { KeyListView } from "./views/servers/KeyListView";
import { ServerDetailView } from "./views/servers/ServerDetailView";
import { ServerFormView } from "./views/servers/ServerFormView";
import { ServerListView } from "./views/servers/ServerListView";
import { ServerTerminalView } from "./views/servers/ServerTerminalView";
import { AccountView } from "./views/settings/AccountView";
import { McpSettingsView } from "./views/settings/McpSettingsView";

export function App() {
  const auth = useAuth();
  const location = useLocation();
  if (!auth.checked) return null;
  if (location.pathname === "/login") {
    if (auth.authenticated) return <Navigate to="/servers" replace />;
    return <LoginView />;
  }
  if (!auth.authenticated) {
    const next = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/login?next=${next}`} replace />;
  }
  return <Shell />;
}

function Shell() {
  const auth = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [openGroup, setOpenGroup] = useState<string | null>(null);
  const path = location.pathname;

  function toggleGroup(name: string, target: string) {
    if (openGroup === name) { setOpenGroup(null); return; }
    setOpenGroup(name);
    if (!path.startsWith(target)) navigate(target);
  }

  async function logout() {
    await auth.logout();
    window.location.assign("/login");
  }

  return (
    <div className="app">
      <aside className="sider">
        <div className="logo"><span className="logo-mark">策</span><span>策略控制台</span></div>
        <nav className="nav">
          <p className="nav-title">概览</p>
          <Link to="/dashboard" className={`nav-item${path.startsWith("/dashboard") ? " is-on" : ""}`} onClick={() => setOpenGroup(null)}>
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <rect x="1.6" y="1.6" width="5.2" height="5.2" rx="1" stroke="currentColor" />
              <rect x="9.2" y="1.6" width="5.2" height="5.2" rx="1" stroke="currentColor" />
              <rect x="1.6" y="9.2" width="5.2" height="5.2" rx="1" stroke="currentColor" />
              <rect x="9.2" y="9.2" width="5.2" height="5.2" rx="1" stroke="currentColor" />
            </svg>
            仪表盘
          </Link>
          <p className="nav-title">运营</p>
          <div className={`nav-group${openGroup === "quant" ? " is-open" : ""}`}>
            <button className="nav-item" type="button" onClick={() => toggleGroup("quant", "/quant")}>
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                <path d="M1.8 11.5 5.6 7.6l2.3 2.2 5.3-6" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M9.6 3.8h3.6V7.4" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              量化交易
              <Caret />
            </button>
            {openGroup === "quant" && (
              <div className="nav-sub">
                <Link to="/quant/crypto" className={`nav-sub-item${path.startsWith("/quant/crypto") ? " is-on" : ""}`}>数字货币</Link>
              </div>
            )}
          </div>
          <p className="nav-title">资源</p>
          <div className={`nav-group${openGroup === "accounts" ? " is-open" : ""}`}>
            <button className="nav-item" type="button" onClick={() => toggleGroup("accounts", "/accounts")}>
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                <rect x="1.6" y="3.4" width="12.8" height="9.2" rx="1.4" stroke="currentColor" />
                <path d="M1.6 6.4h12.8" stroke="currentColor" />
              </svg>
              资金账户
              <Caret />
            </button>
            {openGroup === "accounts" && (
              <div className="nav-sub">
                <Link to="/accounts/crypto" className={`nav-sub-item${path.startsWith("/accounts/crypto") ? " is-on" : ""}`}>数字钱包</Link>
                <Link to="/accounts/cards" className={`nav-sub-item${path.startsWith("/accounts/cards") ? " is-on" : ""}`}>信用卡</Link>
              </div>
            )}
          </div>
          <Link to="/servers" className={`nav-item${path.startsWith("/servers") || path.startsWith("/keys") ? " is-on" : ""}`} onClick={() => setOpenGroup(null)}>
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <rect x="1.5" y="2.5" width="13" height="4" rx="1" stroke="currentColor" />
              <rect x="1.5" y="9.5" width="13" height="4" rx="1" stroke="currentColor" />
              <circle cx="4" cy="4.5" r="0.7" fill="currentColor" />
              <circle cx="4" cy="11.5" r="0.7" fill="currentColor" />
            </svg>
            服务器
          </Link>
        </nav>
        <div className="nav-foot">
          <Link to="/settings" className={`nav-item${path.startsWith("/settings") ? " is-on" : ""}`} onClick={() => setOpenGroup(null)}>
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <circle cx="8" cy="8" r="2" stroke="currentColor" />
              <path d="M8 1.6v1.8M8 12.6v1.8M1.6 8h1.8M12.6 8h1.8M3.4 3.4l1.3 1.3M11.3 11.3l1.3 1.3M3.4 12.6l1.3-1.3M11.3 4.7l1.3-1.3" stroke="currentColor" strokeLinecap="round" />
            </svg>
            平台设置
          </Link>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <TopTabs path={path} />
          <div className="top-actions"><button className="link" type="button" onClick={() => void logout()}>退出</button></div>
        </header>
        <div className="content">
          {auth.passwordIsDefault && <p className="banner">当前仍是默认用户名 admin、密码 changeme。请到「平台设置 / 登录安全」里修改。</p>}
          <Routes>
            <Route path="/" element={<Navigate to="/servers" replace />} />
            <Route path="/dashboard" element={<DashboardView />} />
            <Route path="/servers" element={<ServerListView />} />
            <Route path="/servers/new" element={<ServerFormView />} />
            <Route path="/servers/:id/edit" element={<ServerFormView />} />
            <Route path="/servers/:id/terminal" element={<ServerTerminalView />} />
            <Route path="/servers/:id" element={<ServerDetailView />} />
            <Route path="/keys" element={<KeyListView />} />
            <Route path="/account" element={<Navigate to="/settings" replace />} />
            <Route path="/settings" element={<AccountView />} />
            <Route path="/settings/mcp" element={<McpSettingsView />} />
            <Route path="/accounts/crypto" element={<CryptoAccountView />} />
            <Route path="/accounts/crypto/:id" element={<WalletDetailView />} />
            <Route path="/accounts/cards" element={<CardAccountView />} />
            <Route path="/quant/crypto" element={<QuantOverviewView />} />
            <Route path="/quant/crypto/markets" element={<MarketView />} />
            <Route path="/quant/crypto/exchanges" element={<ExchangeView />} />
            <Route path="/quant/crypto/strategies" element={<QuantStrategyView />} />
          </Routes>
        </div>
      </div>
    </div>
  );
}

function Caret() {
  return (
    <svg className="nav-caret" width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
      <path d="M4.2 2.4 7.8 6 4.2 9.6" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function TopTabs({ path }: { path: string }) {
  if (path.startsWith("/dashboard")) return <nav className="tabs"><Link to="/dashboard" className="tab is-on">仪表盘</Link></nav>;
  if (path.startsWith("/settings")) {
    return (
      <nav className="tabs">
        <Link to="/settings" className={`tab${path === "/settings" ? " is-on" : ""}`}>登录安全</Link>
        <Link to="/settings/mcp" className={`tab${path.startsWith("/settings/mcp") ? " is-on" : ""}`}>MCP</Link>
      </nav>
    );
  }
  if (path.startsWith("/accounts/crypto")) return <nav className="tabs"><Link to="/accounts/crypto" className="tab is-on">钱包实例</Link></nav>;
  if (path.startsWith("/accounts/cards")) return <nav className="tabs"><Link to="/accounts/cards" className="tab is-on">虚拟信用卡</Link></nav>;
  if (path.startsWith("/quant/crypto")) {
    return (
      <nav className="tabs">
        <Link to="/quant/crypto" className={`tab${path === "/quant/crypto" ? " is-on" : ""}`}>概览</Link>
        <Link to="/quant/crypto/markets" className={`tab${path.startsWith("/quant/crypto/markets") ? " is-on" : ""}`}>行情</Link>
        <Link to="/quant/crypto/exchanges" className={`tab${path.startsWith("/quant/crypto/exchanges") ? " is-on" : ""}`}>交易所</Link>
        <Link to="/quant/crypto/strategies" className={`tab${path.startsWith("/quant/crypto/strategies") ? " is-on" : ""}`}>交易策略</Link>
      </nav>
    );
  }
  return (
    <nav className="tabs">
      <Link to="/servers" className={`tab${path.startsWith("/servers") ? " is-on" : ""}`}>服务器实例</Link>
      <Link to="/keys" className={`tab${path.startsWith("/keys") ? " is-on" : ""}`}>服务器密钥</Link>
    </nav>
  );
}
