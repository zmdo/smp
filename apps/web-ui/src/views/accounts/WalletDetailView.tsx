import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ApiError, api, formatTime } from "../../api";

interface Address {
  chain: string;
  chain_label: string;
  address: string;
  derivation_path: string | null;
  source: "derived" | "manual";
}

interface Account {
  id: string;
  name: string;
  derivation_index: number;
  addresses: Address[];
}

interface Wallet {
  id: string;
  name: string;
  created_at: string;
  accounts: Account[];
}

export function WalletDetailView() {
  const { id = "" } = useParams();
  const [wallet, setWallet] = useState<Wallet | null>(null);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState("");

  useEffect(() => {
    api<Wallet>(`/api/wallets/${id}`).then(setWallet).catch((err) => setError(err instanceof ApiError ? err.message : "加载失败"));
  }, [id]);

  async function copy(value: string) {
    await navigator.clipboard.writeText(value);
    setCopied(value);
  }

  return (
    <>
      {error && <p className="banner error">{error}</p>}
      {wallet && (
        <section className="panel">
          <header className="panel-head">
            <h1><i className="mark" />{wallet.name}</h1>
            <div className="tools"><Link className="link" to="/accounts/crypto">返回列表</Link></div>
          </header>
          <div className="panel-body">
            <p className="sub">创建于 {formatTime(wallet.created_at)}</p>
            {wallet.accounts.map((account) => (
              <div key={account.id} className="account-block">
                <h2>{account.name}</h2>
                <div className="table-wrap">
                  <table>
                    <thead><tr><th>链</th><th>收款地址</th><th /></tr></thead>
                    <tbody>
                      {account.addresses.map((item) => (
                        <tr key={item.chain}>
                          <td>{item.chain_label}</td>
                          <td className="mono">{item.address}</td>
                          <td><button className="link" type="button" onClick={() => void copy(item.address)}>{copied === item.address ? "已复制" : "复制"}</button></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}
    </>
  );
}
