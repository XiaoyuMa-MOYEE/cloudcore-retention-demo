import { useEffect, useMemo, useState } from "react";
import { ArrowDownToLine, ArrowUpDown, Check, Cloud, FileUp, Search, ShieldCheck, Sparkles, X } from "lucide-react";
import * as api from "../api";
import type { Customer, Task } from "../types";

const columns: Array<[keyof Customer, string]> = [
  ["customer_id", "Customer ID"], ["industry", "Industry"], ["region", "Region"],
  ["tenure_months", "Tenure"], ["products", "Products"], ["monthly_recurring_revenue", "MRR"],
  ["support_tier", "Support tier"], ["churn_probability", "Churn score"],
];
const number = (value: number) => new Intl.NumberFormat("en-AU", { maximumFractionDigits: 0 }).format(value);

export default function App() {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [selected, setSelected] = useState<Customer | null>(null);
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<keyof Customer>("customer_id");
  const [ascending, setAscending] = useState(true);
  const [task, setTask] = useState<Task | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [upload, setUpload] = useState<File | null>(null);
  const [uploadMessage, setUploadMessage] = useState("");

  useEffect(() => {
    api.getDemo().then((demo) => setCustomers(demo.customers)).catch((e) => setError(e.message));
  }, []);

  const rows = useMemo(() => customers.filter((c) => Object.values(c).join(" ").toLowerCase().includes(search.toLowerCase()))
    .sort((a, b) => {
      const av = a[sort] || ""; const bv = b[sort] || ""; const n = Number(av) - Number(bv);
      const cmp = av !== "" && bv !== "" && Number.isFinite(n) ? n : String(av).localeCompare(String(bv));
      return ascending ? cmp : -cmp;
    }), [customers, search, sort, ascending]);
  const overview = useMemo(() => {
    const distribution: Record<string, number> = {}; let index = 0;
    customers.forEach((c) => { if (c.offer_code) distribution[c.offer_code] = (distribution[c.offer_code] || 0) + 1; index += Number(c.monthly_recurring_revenue) * Number(c.churn_probability); });
    return { distribution, index };
  }, [customers]);

  async function run() {
    setError(""); setTask(null); setBusy(true);
    try {
      const result = await api.analyze(upload || undefined);
      setTask(result);
      const merged = customers.map((c) => ({ ...c, ...(result.results?.find((r) => r.customer_id === c.customer_id) || {}) }));
      setCustomers(merged);
      setSelected((current) => current ? (merged.find((c) => c.customer_id === current.customer_id) || current) : null);
    } catch (e) { setError(e instanceof Error ? e.message : "Analysis failed."); }
    finally { setBusy(false); }
  }

  async function onUpload(file?: File) {
    if (!file) return;
    setUpload(file); setUploadMessage("Validating CSV…"); setError("");
    try {
      const result = await api.validateCsv(file);
      setCustomers(result.customers); setTask(null);
      setUploadMessage(`${result.rows} rows valid. ${result.message}`);
    } catch (e) { setUpload(null); setUploadMessage(""); setError(e instanceof Error ? e.message : "CSV validation failed."); }
  }

  const completed = task?.status === "completed";
  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark"><Cloud size={20} /></div><div><strong>CloudCore</strong><small>RETENTION DEMO</small></div></div>
      <div className="side-label">WORKSPACE</div><div className="nav-item active"><Sparkles size={16} /> Analysis demo</div>
      <div className="sidebar-bottom"><div className="human-callout"><ShieldCheck size={17} /><div><b>Human approval required</b><span>Messages are drafts for review</span></div></div></div>
    </aside>
    <main className="main-content">
      <header className="topbar"><div><span className="crumb">Workspace</span><span className="slash">/</span><b>Analysis demo</b></div><div className="top-tags"><span className={`tag ${upload ? "" : "green"}`}><span />{upload ? "Uploaded CSV" : "Synthetic demo data"}</span><span className="tag">V0.3 PREVIEW</span></div></header>
      <section className="page-heading"><div><p className="eyebrow">RETENTION ANALYSIS</p><h1>Customer overview</h1><p className="muted">{upload ? "Review the validated uploaded customer data and generate personalised offer messages." : "Review the synthetic customer set and generate personalised offer messages."}</p></div><div className="heading-actions"><label className="button secondary upload-button"><FileUp size={16} /> Upload CSV<input type="file" accept=".csv,text/csv" onChange={(e) => onUpload(e.target.files?.[0])} /></label><button className="primary" disabled={busy || !customers.length} onClick={run}><Sparkles size={16} /> {busy ? "Analysis running" : "Run AI analysis"}</button></div></section>
      <div className="notice"><ShieldCheck size={17} /><span>{upload ? <><b>Uploaded CSV validated.</b> Clicking Run AI analysis sends the approved message-generation fields from this file to Azure.</> : <><b>Synthetic demo data.</b> No model call occurs until you click Run AI analysis.</>} Every message needs human review before use.</span></div>
      {uploadMessage && <div className="upload-status"><Check size={15} />{uploadMessage}<button onClick={() => { setUpload(null); setUploadMessage(""); setTask(null); api.getDemo().then((data) => setCustomers(data.customers)); }} aria-label="Remove uploaded file"><X size={15} /></button></div>}
      {error && <div className="alert"><span><b>Request failed.</b> {error}</span><button className="icon-button" onClick={() => setError("")} aria-label="Dismiss"><X size={16} /></button></div>}
      {busy && <section className="progress-card"><div className="progress-top"><div><b>Processing customer messages…</b><span>Offer and Reason are calculated locally; this one-off request does not save server-side progress.</span></div></div></section>}
      {completed && <section className="overview-grid"><div className="metric-card metric-wide"><div className="metric-title">Offer distribution <span>{task.total} CUSTOMER RECORDS</span></div><div className="offer-bars">{["O1", "O2", "O3", "O4"].map((code) => <div className="offer-bar-row" key={code}><b>{code}</b><div className="bar"><i style={{ width: `${customers.length ? ((overview.distribution[code] || 0) / customers.length) * 100 : 0}%` }} /></div><span>{overview.distribution[code] || 0}</span></div>)}</div></div><div className="metric-card"><div className="metric-title">Risk-weighted MRR index <span>INTERNAL</span></div><div className="big-number">{number(task.risk_weighted_mrr_index ?? overview.index)}</div><p>Exploratory review index · not a forecast or expected loss</p></div></section>}
      {completed && <div className="upload-status"><Check size={15} />Analysis complete · Tokens: {task.token_usage?.total_tokens ?? "unavailable"} total (input {task.token_usage?.input_tokens ?? "?"}, output {task.token_usage?.output_tokens ?? "?"})</div>}
      <section className="data-card"><div className="table-header"><div><h2>Customers <span className="count-pill">{customers.length}</span></h2><p>Eight validated input fields{completed ? " · analysis results available" : ""}</p></div><div className="table-tools"><div className="search-box"><Search size={16} /><input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search customers" /></div>{completed && <button className="button secondary download" onClick={() => task.offers_csv && api.downloadCsv(task.offers_csv)}><ArrowDownToLine size={15} /> Export offers.csv</button>}</div></div>
        <div className="table-scroll"><table><thead><tr>{columns.map(([key, label]) => <th key={key}><button onClick={() => { if (sort === key) setAscending(!ascending); else { setSort(key); setAscending(true); } }}>{label}<ArrowUpDown size={12} /></button></th>)}</tr></thead><tbody>{rows.map((customer) => <tr key={customer.customer_id} onClick={() => setSelected(customer)}><td className="id-cell">{customer.customer_id}</td><td>{customer.industry}</td><td>{customer.region}</td><td>{customer.tenure_months} mo</td><td className="product-cell">{customer.products}</td><td>{number(Number(customer.monthly_recurring_revenue))}</td><td><span className={`tier ${customer.support_tier.toLowerCase()}`}>{customer.support_tier}</span></td><td><span className="churn-score">{(Number(customer.churn_probability) * 100).toFixed(0)}%</span><div className="tiny-bar"><i style={{ width: `${Number(customer.churn_probability) * 100}%` }} /></div></td></tr>)}</tbody></table>{!rows.length && <div className="empty">No customers match your search.</div>}</div>
        <footer className="table-footer">Showing {rows.length} of {customers.length} {upload ? "uploaded customers" : "synthetic customers"} <span>Click a row to inspect details</span></footer>
      </section>
      {selected && <div className="overlay" onMouseDown={(e) => e.target === e.currentTarget && setSelected(null)}><aside className="detail-panel"><div className="detail-header"><div><span className="eyebrow">CUSTOMER DETAIL</span><h2>{selected.customer_id}</h2></div><button className="icon-button" onClick={() => setSelected(null)}><X size={18} /></button></div><div className="detail-content"><div className="detail-section"><h3>Input profile</h3><div className="detail-grid">{columns.slice(1).map(([key, label]) => <div key={key}><span>{label}</span><b>{selected[key]}</b></div>)}</div></div>{completed && <><div className="detail-section"><h3>Assigned offer <span className="offer-code">{selected.offer_code}</span></h3><p className="offer-copy">{selected.offer}</p><p className="reason-copy">{selected.reason}</p></div><div className="detail-section message-box"><h3>Message <span>HUMAN REVIEW REQUIRED</span></h3><p>{selected.message || "No message available."}</p></div></>}</div><div className="detail-foot"><ShieldCheck size={16} /> {upload ? "Uploaded Data" : "Synthetic Data"} · Human Approval Required</div></aside></div>}
    </main>
  </div>;
}
