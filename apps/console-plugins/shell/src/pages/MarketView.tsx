import { createChart, type CandlestickData, type IChartApi, type ISeriesApi } from "lightweight-charts";
import { FormEvent, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { ApiError, api } from "../api";

interface Venue { id: string; name: string; wallet: string }
interface Candle { time: number; open: number; high: number; low: number; close: number; volume: number }
interface Quote {
  symbol: string; timeframe: string; last: string | null; bid: string | null; ask: string | null;
  high: string | null; low: string | null; percentage: string | null; change: string | null;
  base_volume: string | null; quote_volume: string | null; candles: Candle[];
}

const periods = [
  { id: "1m", label: "1 分钟" },
  { id: "15m", label: "15 分钟" },
  { id: "1h", label: "1 小时" },
  { id: "4h", label: "4 小时" },
  { id: "1d", label: "1 日" },
];

export function MarketView() {
  const [venues, setVenues] = useState<Venue[]>([]);
  const [venueId, setVenueId] = useState("binance");
  const [symbol, setSymbol] = useState("BTC/USDT");
  const [timeframe, setTimeframe] = useState("1h");
  const [quote, setQuote] = useState<Quote | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const hostRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);

  const changeClass = useMemo(() => {
    const value = Number(quote?.percentage);
    if (!quote?.percentage || Number.isNaN(value) || value === 0) return "";
    return value > 0 ? "up" : "down";
  }, [quote]);
  const changeText = useMemo(() => {
    if (!quote?.percentage) return "—";
    const value = Number(quote.percentage);
    return `${value > 0 ? "+" : ""}${quote.percentage}%`;
  }, [quote]);

  useEffect(() => {
    api<Venue[]>("/api/exchanges/venues").then((items) => {
      setVenues(items);
      setVenueId((current) => (items.some((item) => item.id === current) ? current : items[0]?.id || current));
    }).catch((err) => setError(err instanceof ApiError ? err.message : "加载失败"));
  }, []);

  async function search(event: FormEvent) {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      const params = new URLSearchParams({ venue: venueId, symbol, timeframe });
      setQuote(await api<Quote>(`/api/markets/quote?${params}`));
    } catch (err) {
      setQuote(null);
      setError(err instanceof ApiError ? err.message : "查询行情失败");
    } finally {
      setLoading(false);
    }
  }

  useLayoutEffect(() => {
    const host = hostRef.current;
    const candles = quote?.candles || [];
    if (!host || candles.length === 0) {
      chartRef.current?.remove();
      chartRef.current = null;
      seriesRef.current = null;
      return;
    }
    if (!chartRef.current || !seriesRef.current) {
      const chart = createChart(host, {
        width: host.clientWidth,
        height: 420,
        layout: { background: { color: "#ffffff" }, textColor: "#606266" },
        grid: { vertLines: { color: "#f2f3f5" }, horzLines: { color: "#f2f3f5" } },
        timeScale: { timeVisible: timeframe !== "1d", secondsVisible: false },
        rightPriceScale: { borderColor: "#e8eaed" },
      });
      chartRef.current = chart;
      seriesRef.current = chart.addCandlestickSeries({
        upColor: "#1f9d55", downColor: "#e5484d", borderVisible: false, wickUpColor: "#1f9d55", wickDownColor: "#e5484d",
      });
    }
    seriesRef.current.setData(candles as unknown as CandlestickData[]);
    chartRef.current.timeScale().fitContent();
    chartRef.current.applyOptions({ width: host.clientWidth, timeScale: { timeVisible: timeframe !== "1d" } });
  }, [quote, timeframe]);

  useEffect(() => () => {
    chartRef.current?.remove();
    chartRef.current = null;
    seriesRef.current = null;
  }, []);

  return (
    <>
      {error && <p className="banner error">{error}</p>}
      <section className="panel">
        <header className="panel-head"><h1><i className="mark" />行情</h1></header>
        <div className="panel-body">
          <form className="panel-form" onSubmit={search}>
            <p className="muted" style={{ marginTop: 0 }}>选择交易所和交易码查看现货行情。交易码写成 BTC/USDT，四家通用。这里只读取公开行情，不会下单。</p>
            <div className="triple">
              <label>交易所
                <select value={venueId} onChange={(event) => setVenueId(event.target.value)}>
                  {venues.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                </select>
              </label>
              <label>交易码<input value={symbol} required maxLength={40} placeholder="BTC/USDT" onChange={(event) => setSymbol(event.target.value)} /></label>
              <label>周期
                <select value={timeframe} onChange={(event) => setTimeframe(event.target.value)}>
                  {periods.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
                </select>
              </label>
            </div>
            <button className="primary" type="submit" disabled={loading}>{loading ? "查询中" : "查看行情"}</button>
          </form>
          {quote && (
            <>
              <dl className="quote-stats">
                <div><dt>最新价</dt><dd>{quote.last || "—"}</dd></div>
                <div><dt>24 小时涨跌</dt><dd className={changeClass}>{changeText}</dd></div>
                <div><dt>最高</dt><dd>{quote.high || "—"}</dd></div>
                <div><dt>最低</dt><dd>{quote.low || "—"}</dd></div>
                <div><dt>买一</dt><dd>{quote.bid || "—"}</dd></div>
                <div><dt>卖一</dt><dd>{quote.ask || "—"}</dd></div>
                <div><dt>成交量</dt><dd>{quote.base_volume || "—"}</dd></div>
                <div><dt>成交额</dt><dd>{quote.quote_volume || "—"}</dd></div>
              </dl>
              {quote.candles.length ? <div ref={hostRef} className="chart-box" /> : <p className="empty">没有 K 线。</p>}
            </>
          )}
        </div>
      </section>
    </>
  );
}
