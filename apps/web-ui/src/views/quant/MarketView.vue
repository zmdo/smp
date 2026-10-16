<script setup lang="ts">
import { createChart, type IChartApi, type ISeriesApi, type CandlestickData } from "lightweight-charts";
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { ApiError, api } from "../../api";

interface Venue {
  id: string;
  name: string;
  wallet: string;
}

interface Candle {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface Quote {
  symbol: string;
  timeframe: string;
  last: string | null;
  bid: string | null;
  ask: string | null;
  high: string | null;
  low: string | null;
  percentage: string | null;
  change: string | null;
  base_volume: string | null;
  quote_volume: string | null;
  candles: Candle[];
}

const periods = [
  { id: "1m", label: "1 分钟" },
  { id: "15m", label: "15 分钟" },
  { id: "1h", label: "1 小时" },
  { id: "4h", label: "4 小时" },
  { id: "1d", label: "1 日" },
];

const venues = ref<Venue[]>([]);
const venueId = ref("binance");
const symbol = ref("BTC/USDT");
const timeframe = ref("1h");
const quote = ref<Quote | null>(null);
const error = ref("");
const loading = ref(false);
const chartHost = ref<HTMLElement | null>(null);
let chart: IChartApi | null = null;
let series: ISeriesApi<"Candlestick"> | null = null;

const changeClass = computed(() => {
  const value = Number(quote.value?.percentage);
  if (!quote.value?.percentage || Number.isNaN(value) || value === 0) return "";
  return value > 0 ? "up" : "down";
});

const changeText = computed(() => {
  if (!quote.value?.percentage) return "—";
  const value = Number(quote.value.percentage);
  const sign = value > 0 ? "+" : "";
  return `${sign}${quote.value.percentage}%`;
});

watch(venues, (items) => {
  if (!items.some((item) => item.id === venueId.value) && items[0]) venueId.value = items[0].id;
});

loadVenues();

async function loadVenues() {
  try {
    venues.value = await api<Venue[]>("/api/exchanges/venues");
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : "加载失败";
  }
}

async function search() {
  error.value = "";
  loading.value = true;
  try {
    const params = new URLSearchParams({ venue: venueId.value, symbol: symbol.value, timeframe: timeframe.value });
    quote.value = await api<Quote>(`/api/markets/quote?${params}`);
  } catch (err) {
    quote.value = null;
    error.value = err instanceof ApiError ? err.message : "查询行情失败";
  } finally {
    loading.value = false;
  }
}

watch(
  () => [quote.value, chartHost.value] as const,
  () => draw(),
  { flush: "post" },
);

function draw() {
  const host = chartHost.value;
  const candles = quote.value?.candles || [];
  if (!host || candles.length === 0) {
    removeChart();
    return;
  }
  if (!chart || !series) {
    chart = createChart(host, {
      width: host.clientWidth,
      height: 420,
      layout: { background: { color: "#ffffff" }, textColor: "#606266" },
      grid: { vertLines: { color: "#f2f3f5" }, horzLines: { color: "#f2f3f5" } },
      timeScale: { timeVisible: timeframe.value !== "1d", secondsVisible: false },
      rightPriceScale: { borderColor: "#e8eaed" },
    });
    series = chart.addCandlestickSeries({
      upColor: "#1f9d55",
      downColor: "#e5484d",
      borderVisible: false,
      wickUpColor: "#1f9d55",
      wickDownColor: "#e5484d",
    });
  }
  series.setData(candles as CandlestickData[]);
  chart.timeScale().fitContent();
  chart.applyOptions({ width: host.clientWidth, timeScale: { timeVisible: timeframe.value !== "1d" } });
}

function removeChart() {
  chart?.remove();
  chart = null;
  series = null;
}

onBeforeUnmount(removeChart);
</script>

<template>
  <p v-if="error" class="banner error">{{ error }}</p>
  <section class="panel">
    <header class="panel-head">
      <h1><i class="mark"></i>行情</h1>
    </header>
    <div class="panel-body">
      <form class="panel-form" @submit.prevent="search">
        <p class="muted" style="margin-top: 0">选择交易所和交易码查看现货行情。交易码写成 BTC/USDT，四家通用。这里只读取公开行情，不会下单。</p>
        <div class="triple">
          <label>
            交易所
            <select v-model="venueId">
              <option v-for="item in venues" :key="item.id" :value="item.id">{{ item.name }}</option>
            </select>
          </label>
          <label>
            交易码
            <input v-model="symbol" required maxlength="40" placeholder="BTC/USDT" />
          </label>
          <label>
            周期
            <select v-model="timeframe">
              <option v-for="item in periods" :key="item.id" :value="item.id">{{ item.label }}</option>
            </select>
          </label>
        </div>
        <button class="primary" type="submit" :disabled="loading">{{ loading ? "查询中" : "查看行情" }}</button>
      </form>
      <template v-if="quote">
        <dl class="quote-stats">
          <div>
            <dt>最新价</dt>
            <dd>{{ quote.last || "—" }}</dd>
          </div>
          <div>
            <dt>24 小时涨跌</dt>
            <dd :class="changeClass">{{ changeText }}</dd>
          </div>
          <div>
            <dt>最高</dt>
            <dd>{{ quote.high || "—" }}</dd>
          </div>
          <div>
            <dt>最低</dt>
            <dd>{{ quote.low || "—" }}</dd>
          </div>
          <div>
            <dt>买一</dt>
            <dd>{{ quote.bid || "—" }}</dd>
          </div>
          <div>
            <dt>卖一</dt>
            <dd>{{ quote.ask || "—" }}</dd>
          </div>
          <div>
            <dt>成交量</dt>
            <dd>{{ quote.base_volume || "—" }}</dd>
          </div>
          <div>
            <dt>成交额</dt>
            <dd>{{ quote.quote_volume || "—" }}</dd>
          </div>
        </dl>
        <div v-if="quote.candles.length" ref="chartHost" class="chart-box"></div>
        <p v-else class="empty">没有 K 线。</p>
      </template>
    </div>
  </section>
</template>
