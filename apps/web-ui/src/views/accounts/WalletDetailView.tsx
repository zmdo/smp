import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ApiError, api, formatTime } from "../../api";
import { CopyButton } from "../../components/CopyButton";

interface Wallet {
  id: string;
  name: string;
  address: string;
  created_at: string;
}

export function WalletDetailView() {
  const { id = "" } = useParams();
  const [wallet, setWallet] = useState<Wallet | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<Wallet>(`/api/wallets/${id}`).then(setWallet).catch((err) => setError(err instanceof ApiError ? err.message : "账户加载失败"));
  }, [id]);

  if (!wallet) return error ? <p className="banner error">{error}</p> : null;
  return (
    <section>
      <div className="page-head">
        <div>
          <p className="eyebrow">数字货币账户</p>
          <h1>{wallet.name}</h1>
        </div>
        <Link className="secondary button" to="/accounts/crypto">返回</Link>
      </div>
      {error && <p className="banner error">{error}</p>}
      <section className="panel">
        <dl className="facts">
          <div><dt>地址</dt><dd className="mono copy-line">{wallet.address}<CopyButton value={wallet.address} /></dd></div>
          <div><dt>创建时间</dt><dd>{formatTime(wallet.created_at)}</dd></div>
        </dl>
      </section>
    </section>
  );
}
