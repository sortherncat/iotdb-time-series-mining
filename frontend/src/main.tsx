import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import * as echarts from "echarts";
import { Activity, BarChart3, GitBranch, Layers3 } from "lucide-react";
import "./styles.css";

type SegmentMethod = "ruptures_pelt" | "window_stat_distance";
type Algorithm = "kmeans" | "gmm";
type DesignMode = "light" | "dark";

type DataPoint = Record<string, number | string>;
type Segment = [number, number];
type ClusterPoint = {
  segment_id: number;
  x: number;
  y: number;
  condition_id: string;
  segment_start: number;
  segment_end: number;
  start_time: string;
  end_time: string;
  duration_hours: number;
};
type DashboardData = {
  metadata: { row_count: number; sensor_count: number; sensors: string[] };
  timeseries: DataPoint[];
  segments: Record<SegmentMethod, { change_points: number[]; segments: Segment[] }>;
  clusters: Record<
    SegmentMethod,
    Record<
      Algorithm,
      {
        selected_k: number;
        points: ClusterPoint[];
        centers: { condition_id: string; x: number; y: number }[];
        summary: Record<string, string | number>[];
        representatives: Record<
          string,
          { segment_id: number; values: DataPoint[]; start_time: string; end_time: string }[]
        >;
      }
    >
  >;
};

const methodLabels: Record<SegmentMethod, string> = {
  ruptures_pelt: "方案 A · ruptures",
  window_stat_distance: "方案 B · 滑动窗口统计距离",
};

const sensors = [
  "oil_temperature",
  "high_useful_load",
  "middle_useful_load",
  "low_useful_load",
  "high_useless_load",
  "middle_useless_load",
  "low_useless_load",
];

const palette = {
  light: ["#0066cc", "#7a7a7a", "#34c759", "#ff9f0a", "#af52de"],
  dark: ["#fcd535", "#0ecb81", "#f6465d", "#2dbdb6", "#3b82f6"],
};

function Chart({ option, className }: { option: echarts.EChartsOption; className?: string }) {
  const ref = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current);
    chart.setOption(option, true);
    const resize = () => chart.resize();
    window.addEventListener("resize", resize);
    return () => {
      window.removeEventListener("resize", resize);
      chart.dispose();
    };
  }, [option]);
  return <div ref={ref} className={className ?? "chart"} />;
}

function App() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [mode, setMode] = useState<DesignMode>("dark");
  const [method, setMethod] = useState<SegmentMethod>("ruptures_pelt");
  const [algorithm, setAlgorithm] = useState<Algorithm>("kmeans");
  const [activeSensor, setActiveSensor] = useState("oil_temperature");
  const [visibleSensors, setVisibleSensors] = useState<string[]>([
    "oil_temperature",
    "high_useful_load",
    "middle_useful_load",
    "low_useful_load",
  ]);
  const [tab, setTab] = useState("series");

  useEffect(() => {
    fetch("/data/dashboard_data.json")
      .then((response) => response.json())
      .then(setData);
  }, []);

  const cluster = data?.clusters[method][algorithm];
  const conditionCount = cluster?.summary.length ?? 0;

  const chartTheme = mode === "light" ? "light" : "dark";
  const colors = palette[mode];

  const timeSeriesOption = useMemo(() => {
    if (!data) return {};
    const methodSegments = data.segments[method].segments;
    const x = data.timeseries.map((row) => row.datetime);
    const markLines = data.segments[method].change_points
      .map((point) => data.timeseries[Math.floor(point / Math.max(1, data.metadata.row_count / data.timeseries.length))])
      .filter(Boolean)
      .map((row) => ({ xAxis: row.datetime }));
    const markAreas = methodSegments.slice(0, 24).map((segment, index) => {
      const scale = data.metadata.row_count / data.timeseries.length;
      const start = data.timeseries[Math.min(Math.floor(segment[0] / scale), data.timeseries.length - 1)];
      const end = data.timeseries[Math.min(Math.floor(segment[1] / scale), data.timeseries.length - 1)];
      return [
        { xAxis: start.datetime, itemStyle: { color: index % 2 ? "rgba(252,213,53,0.05)" : "rgba(0,102,204,0.05)" } },
        { xAxis: end.datetime },
      ];
    });
    return {
      backgroundColor: "transparent",
      color: colors,
      tooltip: { trigger: "axis" },
      legend: { top: 0, textStyle: { color: chartTheme === "dark" ? "#eaecef" : "#1d1d1f" } },
      grid: { left: 44, right: 24, top: 48, bottom: 42 },
      xAxis: { type: "category", data: x, axisLabel: { color: chartTheme === "dark" ? "#929aa5" : "#7a7a7a" } },
      yAxis: { type: "value", scale: true, axisLabel: { color: chartTheme === "dark" ? "#929aa5" : "#7a7a7a" } },
      series: visibleSensors.map((sensor) => ({
        name: sensor,
        type: "line",
        showSymbol: false,
        smooth: true,
        data: data.timeseries.map((row) => row[sensor]),
        markLine: {
          symbol: "none",
          lineStyle: { type: "dashed", color: mode === "light" ? "#0066cc" : "#fcd535", opacity: 0.55 },
          data: markLines,
        },
        markArea: { silent: true, data: markAreas },
      })),
    };
  }, [data, method, visibleSensors, mode, colors, chartTheme]);

  const scatterOption = useMemo(() => {
    if (!cluster) return {};
    return {
      backgroundColor: "transparent",
      color: colors,
      tooltip: { formatter: (p: any) => `${p.data[3]}<br/>segment ${p.data[2]}` },
      legend: { top: 0, textStyle: { color: chartTheme === "dark" ? "#eaecef" : "#1d1d1f" } },
      grid: { left: 44, right: 24, top: 46, bottom: 42 },
      xAxis: { name: "PC1", axisLabel: { color: chartTheme === "dark" ? "#929aa5" : "#7a7a7a" } },
      yAxis: { name: "PC2", axisLabel: { color: chartTheme === "dark" ? "#929aa5" : "#7a7a7a" } },
      series: [
        ...Array.from(new Set(cluster.points.map((p) => p.condition_id))).map((condition) => ({
          name: condition,
          type: "scatter",
          symbolSize: 14,
          data: cluster.points.filter((p) => p.condition_id === condition).map((p) => [p.x, p.y, p.segment_id, p.condition_id]),
        })),
        {
          name: "center",
          type: "scatter",
          symbol: "diamond",
          symbolSize: 26,
          itemStyle: { borderColor: chartTheme === "dark" ? "#fff" : "#111", borderWidth: 2 },
          data: cluster.centers.map((c) => [c.x, c.y, c.condition_id]),
        },
      ],
    };
  }, [cluster, colors, chartTheme]);

  const representativeOption = useMemo(() => {
    if (!cluster) return {};
    const series = Object.entries(cluster.representatives).flatMap(([condition, reps], conditionIndex) =>
      reps.map((rep) => ({
        name: `${condition} · S${rep.segment_id}`,
        type: "line",
        showSymbol: false,
        smooth: true,
        lineStyle: { opacity: 0.75, width: 2 },
        itemStyle: { color: colors[conditionIndex % colors.length] },
        data: rep.values.map((row, index) => [index, row[activeSensor]]),
      })),
    );
    return {
      backgroundColor: "transparent",
      tooltip: { trigger: "axis" },
      grid: { left: 44, right: 24, top: 30, bottom: 42 },
    xAxis: { type: "value", name: "相对步长", axisLabel: { color: chartTheme === "dark" ? "#929aa5" : "#7a7a7a" } },
      yAxis: { type: "value", scale: true, name: activeSensor, axisLabel: { color: chartTheme === "dark" ? "#929aa5" : "#7a7a7a" } },
      series,
    };
  }, [cluster, activeSensor, colors, chartTheme]);

  const timelineOption = useMemo(() => {
    if (!cluster) return {};
    return {
      backgroundColor: "transparent",
      tooltip: { formatter: (p: any) => `${p.data.condition}<br/>${p.data.start}<br/>${p.data.end}<br/>${p.data.duration}h` },
      grid: { left: 12, right: 24, top: 24, bottom: 38 },
      xAxis: { type: "time", axisLabel: { color: chartTheme === "dark" ? "#929aa5" : "#7a7a7a" } },
      yAxis: { type: "category", data: ["condition"], show: false },
      series: [
        {
          type: "custom",
          renderItem: (params: any, api: any) => {
            const start = api.coord([api.value(0), 0]);
            const end = api.coord([api.value(1), 0]);
            const height = 34;
            return {
              type: "rect",
              shape: { x: start[0], y: start[1] - height / 2, width: Math.max(1, end[0] - start[0]), height },
              style: api.style(),
            };
          },
          encode: { x: [0, 1], y: 2 },
          data: cluster.points.map((p, index) => ({
            value: [p.start_time, p.end_time, 0],
            condition: p.condition_id,
            start: p.start_time,
            end: p.end_time,
            duration: p.duration_hours,
            itemStyle: { color: colors[index % colors.length] },
          })),
        },
      ],
    };
  }, [cluster, colors, chartTheme]);

  if (!data || !cluster) return <main className="loading">正在加载可视化数据...</main>;

  const rootClass = mode === "light" ? "app light" : "app dark";

  return (
    <main className={rootClass}>
      <nav className="topbar">
        <div className="brand">IoTDB 工况识别可视化</div>
        <div className="mode-switch">
          <button className={mode === "light" ? "selected" : ""} onClick={() => setMode("light")}>Light</button>
          <button className={mode === "dark" ? "selected" : ""} onClick={() => setMode("dark")}>Dark</button>
        </div>
      </nav>

      <section className="hero">
        <div>
          <p className="eyebrow">ETTh1 · 7 维传感器 · IoTDB 数据链路</p>
          <h1>高维时间序列分段、特征聚类与工况识别展示。</h1>
        </div>
        <div className="metrics">
          <Metric icon={<Activity />} label="时间点数" value={data.metadata.row_count.toLocaleString()} />
          <Metric icon={<GitBranch />} label="分段数量" value={data.segments[method].segments.length} />
          <Metric icon={<Layers3 />} label="工况数量" value={conditionCount} />
          <Metric icon={<BarChart3 />} label="最优 K" value={cluster.selected_k} />
        </div>
      </section>

      <section className="workspace">
        <aside className="controls">
          <Control label="主题风格">
            <select value={mode} onChange={(e) => setMode(e.target.value as DesignMode)}>
              <option value="light">Light</option>
              <option value="dark">Dark</option>
            </select>
          </Control>
          <Control label="分段方法">
            <select value={method} onChange={(e) => setMethod(e.target.value as SegmentMethod)}>
              <option value="ruptures_pelt">{methodLabels.ruptures_pelt}</option>
              <option value="window_stat_distance">{methodLabels.window_stat_distance}</option>
            </select>
          </Control>
          <Control label="聚类算法">
            <select value={algorithm} onChange={(e) => setAlgorithm(e.target.value as Algorithm)}>
              <option value="kmeans">K-Means</option>
              <option value="gmm">GMM</option>
            </select>
          </Control>
          <Control label="代表片段变量">
            <select value={activeSensor} onChange={(e) => setActiveSensor(e.target.value)}>
              {sensors.map((sensor) => <option key={sensor}>{sensor}</option>)}
            </select>
          </Control>
          <div className="sensor-list">
            {sensors.map((sensor) => (
              <label key={sensor}>
                <input
                  type="checkbox"
                  checked={visibleSensors.includes(sensor)}
                  onChange={() =>
                    setVisibleSensors((current) =>
                      current.includes(sensor) ? current.filter((item) => item !== sensor) : [...current, sensor],
                    )
                  }
                />
                {sensor}
              </label>
            ))}
          </div>
        </aside>

        <section className="panel">
          <div className="tabs">
            {[
              ["series", "多通道时序"],
              ["scatter", "聚类散点"],
              ["representatives", "代表片段"],
              ["timeline", "工况时间线"],
            ].map(([key, label]) => (
              <button key={key} className={tab === key ? "active" : ""} onClick={() => setTab(key)}>
                {label}
              </button>
            ))}
          </div>
          {tab === "series" && <Chart option={timeSeriesOption} className="chart tall" />}
          {tab === "scatter" && <Chart option={scatterOption} className="chart tall" />}
          {tab === "representatives" && <Chart option={representativeOption} className="chart tall" />}
          {tab === "timeline" && <Chart option={timelineOption} className="chart timeline" />}
          <table className="summary">
            <thead>
              <tr>
                <th>工况</th>
                <th>分段数</th>
                <th>总时长/h</th>
                <th>平均时长/h</th>
              </tr>
            </thead>
            <tbody>
              {cluster.summary.map((row) => (
                <tr key={String(row.condition_id)}>
                  <td>{row.condition_id}</td>
                  <td>{row.segment_count}</td>
                  <td>{Number(row.total_duration_hours).toFixed(0)}</td>
                  <td>{Number(row.mean_duration_hours).toFixed(1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </section>
    </main>
  );
}

function Metric({ icon, label, value }: { icon: React.ReactNode; label: string; value: string | number }) {
  return (
    <div className="metric">
      <span>{icon}</span>
      <small>{label}</small>
      <strong>{value}</strong>
    </div>
  );
}

function Control({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="control">
      <span>{label}</span>
      {children}
    </label>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
