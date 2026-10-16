import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { ApiError, api } from "../../../shared/src/api";
import placesJson from "../geo/places.json";

interface UsState {
  code: string;
  name: string;
  cities: string[];
}

const places = placesJson as { countries: string[]; usStates: UsState[] };
const countries = places.countries;
const usStates = places.usStates;
const unitedStates = "United States";

interface Card {
  id: string;
  name: string;
  platform: string;
  holder: string;
  expiry: string;
  last4: string;
  country: string;
  region: string;
  city: string;
  address1: string;
  address2: string;
  postal_code: string;
  note: string;
  created_at: string;
}

export function CardAccountView() {
  const [cards, setCards] = useState<Card[]>([]);
  const [error, setError] = useState("");
  const [creating, setCreating] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [name, setName] = useState("");
  const [platform, setPlatform] = useState("");
  const [holder, setHolder] = useState("");
  const [number, setNumber] = useState("");
  const [expiry, setExpiry] = useState("");
  const [cvv, setCvv] = useState("");
  const [country, setCountry] = useState(unitedStates);
  const [region, setRegion] = useState("");
  const [city, setCity] = useState("");
  const [stateOpen, setStateOpen] = useState(false);
  const [address1, setAddress1] = useState("");
  const [address2, setAddress2] = useState("");
  const [postalCode, setPostalCode] = useState("");
  const [note, setNote] = useState("");
  const [revealed, setRevealed] = useState<Record<string, { number: string; cvv: string }>>({});
  const statePick = useRef<HTMLDivElement>(null);
  const isUnitedStates = country === unitedStates;
  const cities = useMemo(() => usStates.find((item) => item.name === region)?.cities ?? [], [region]);
  const selectedState = usStates.find((item) => item.name === region);

  async function load() {
    try {
      setCards(await api<Card[]>("/api/cards"));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "加载失败");
    }
  }

  useEffect(() => {
    void load();
    function closeStateMenu(event: Event) {
      if (!statePick.current?.contains(event.target as Node)) setStateOpen(false);
    }
    document.addEventListener("pointerdown", closeStateMenu);
    return () => document.removeEventListener("pointerdown", closeStateMenu);
  }, []);

  async function create(event: FormEvent) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await api("/api/cards", {
        method: "POST",
        body: JSON.stringify({
          name, platform, holder, number, expiry, cvv, country, region, city, address1, address2,
          postal_code: postalCode, note,
        }),
      });
      setName(""); setPlatform(""); setHolder(""); setNumber(""); setExpiry(""); setCvv("");
      setCountry(unitedStates); setRegion(""); setCity(""); setAddress1(""); setAddress2("");
      setPostalCode(""); setNote(""); setCreating(false);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "保存失败");
    } finally {
      setSubmitting(false);
    }
  }

  async function reveal(item: Card) {
    setError("");
    if (revealed[item.id]) {
      setRevealed((current) => {
        const next = { ...current };
        delete next[item.id];
        return next;
      });
      return;
    }
    try {
      const secret = await api<{ number: string; cvv: string }>(`/api/cards/${item.id}/secret`);
      setRevealed((current) => ({ ...current, [item.id]: secret }));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "无法查看");
    }
  }

  function billing(item: Card) {
    const street = [item.address1, item.address2].filter(Boolean).join(" ");
    return [street, item.city, item.region, item.country, item.postal_code].filter(Boolean).join(", ");
  }

  async function remove(item: Card) {
    if (!window.confirm(`删除虚拟信用卡「${item.name}」？`)) return;
    setError("");
    try {
      await api(`/api/cards/${item.id}`, { method: "DELETE" });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "删除失败");
    }
  }

  return (
    <>
      {error && <p className="banner error">{error}</p>}
      {creating && (
        <section className="panel">
          <header className="panel-head"><h1><i className="mark" />添加虚拟信用卡</h1></header>
          <div className="panel-body">
            <form className="panel-form" onSubmit={create}>
              <label>平台<input value={platform} required maxLength={80} placeholder="这张卡来自哪个平台" onChange={(event) => setPlatform(event.target.value)} /></label>
              <label>名称<input value={name} required maxLength={80} placeholder="例如 日常消费" onChange={(event) => setName(event.target.value)} /></label>
              <label>持卡人<input value={holder} required maxLength={80} onChange={(event) => setHolder(event.target.value)} /></label>
              <label>卡号<input value={number} required inputMode="numeric" autoComplete="off" placeholder="可带空格" onChange={(event) => setNumber(event.target.value)} /></label>
              <label>有效期<input value={expiry} required maxLength={5} placeholder="MM/YY" onChange={(event) => setExpiry(event.target.value)} /></label>
              <label>安全码<input value={cvv} required maxLength={4} inputMode="numeric" autoComplete="off" onChange={(event) => setCvv(event.target.value)} /></label>
              <div className="triple">
                <label>国家
                  <select value={country} required onChange={(event) => { setCountry(event.target.value); setRegion(""); setCity(""); setStateOpen(false); }}>
                    {countries.map((item) => <option key={item} value={item}>{item}</option>)}
                  </select>
                </label>
                <div className="field">
                  <span>地区/州</span>
                  {isUnitedStates ? (
                    <div ref={statePick} className="state-pick">
                      <button type="button" className="state-trigger" onClick={() => setStateOpen((open) => !open)}>
                        {selectedState ? <span>(<strong>{selectedState.code}</strong>) {selectedState.name}</span> : <span className="placeholder">请选择</span>}
                      </button>
                      {stateOpen && (
                        <div className="state-menu">
                          {usStates.map((item) => (
                            <button key={item.code} type="button" className={item.name === region ? "on" : ""} onClick={() => { setRegion(item.name); setCity(""); setStateOpen(false); }}>
                              (<strong>{item.code}</strong>) {item.name}
                            </button>
                          ))}
                        </div>
                      )}
                      <input className="state-proxy" value={region} required tabIndex={-1} onChange={() => undefined} onInvalid={() => setStateOpen(true)} />
                    </div>
                  ) : (
                    <input value={region} required maxLength={80} onChange={(event) => setRegion(event.target.value)} />
                  )}
                </div>
                <label>市
                  {isUnitedStates ? (
                    <select value={city} required disabled={!region} onChange={(event) => setCity(event.target.value)}>
                      <option value="" disabled>请选择</option>
                      {cities.map((item) => <option key={item} value={item}>{item}</option>)}
                    </select>
                  ) : (
                    <input value={city} required maxLength={80} onChange={(event) => setCity(event.target.value)} />
                  )}
                </label>
              </div>
              <label>地址1<input value={address1} required maxLength={160} onChange={(event) => setAddress1(event.target.value)} /></label>
              <label>地址2<input value={address2} maxLength={160} placeholder="可不填" onChange={(event) => setAddress2(event.target.value)} /></label>
              <label>邮编<input value={postalCode} required maxLength={20} onChange={(event) => setPostalCode(event.target.value)} /></label>
              <label>备注<input value={note} maxLength={500} onChange={(event) => setNote(event.target.value)} /></label>
              <div className="row">
                <button className="primary" type="submit" disabled={submitting}>保存</button>
                <button className="link" type="button" onClick={() => setCreating(false)}>取消</button>
              </div>
            </form>
          </div>
        </section>
      )}
      <section className="panel">
        <header className="panel-head">
          <h1><i className="mark" />虚拟信用卡 <em className="count">{cards.length}</em></h1>
          <div className="tools"><button className="icon" type="button" title="添加虚拟信用卡" onClick={() => setCreating(true)}>+</button></div>
        </header>
        {cards.length === 0 ? <div className="empty">还没有虚拟信用卡。点右上角添加。</div> : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>平台</th><th>名称</th><th>卡号</th><th>持卡人</th><th>账单地址</th><th>有效期</th><th>操作</th></tr></thead>
              <tbody>
                {cards.map((item) => (
                  <tr key={item.id}>
                    <td>{item.platform}</td>
                    <td>{item.name}</td>
                    <td className="mono">{revealed[item.id] ? `${revealed[item.id].number} · ${revealed[item.id].cvv}` : `•••• ${item.last4}`}</td>
                    <td>{item.holder}</td>
                    <td>{billing(item)}</td>
                    <td>{item.expiry}</td>
                    <td>
                      <button className="link" type="button" onClick={() => void reveal(item)}>{revealed[item.id] ? "隐藏" : "查看"}</button>
                      <button className="link danger" type="button" onClick={() => void remove(item)}>删除</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <footer className="panel-foot">共 {cards.length} 条</footer>
      </section>
    </>
  );
}
