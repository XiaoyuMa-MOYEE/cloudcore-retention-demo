import { useEffect, useMemo, useState } from "react";
import {
  ArrowDownToLine,
  ArrowUpDown,
  Check,
  ChevronRight,
  CircleAlert,
  Cloud,
  FileUp,
  LockKeyhole,
  LogOut,
  Search,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";
import * as api from "../api";
import type { Customer, Task } from "../types";

const columns: Array<[keyof Customer, string]> = [
  ["customer_id", "Customer ID"],
  ["industry", "Industry"],
  ["region", "Region"],
  ["tenure_months", "Tenure"],
  ["products", "Products"],
  ["monthly_recurring_revenue", "MRR"],
  ["support_tier", "Support tier"],
  ["churn_probability", "Churn score"],
];
const number = (value: number) =>
  new Intl.NumberFormat("en-AU", { maximumFractionDigits: 0 }).format(value);

export default function App() {
  const [authenticated, setAuthenticated] = useState(false);
  const [checking, setChecking] = useState(true);
  const [accessCode, setAccessCode] = useState("");
  const [loginError, setLoginError] = useState("");
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [selected, setSelected] = useState<Customer | null>(null);
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<keyof Customer>("customer_id");
  const [ascending, setAscending] = useState(true);
  const [task, setTask] = useState<Task | null>(null);
  const [taskId, setTaskId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [upload, setUpload] = useState<File | null>(null);
  const [uploadMessage, setUploadMessage] = useState("");
  const [uploadAllowed, setUploadAllowed] = useState(true);
  const [syntheticData, setSyntheticData] = useState(true);

  useEffect(() => {
    api
      .getSession()
      .then((x) => setAuthenticated(x.authenticated))
      .catch(() => {})
      .finally(() => setChecking(false));
  }, []);
  useEffect(() => {
    if (!authenticated) return;
    Promise.all([api.getDemo(), api.getLatestTask()])
      .then(([demo, latest]) => {
        setCustomers(demo.customers);
        if (!latest.task) return;
        const previous = latest.task;
        setTask(previous);
        setTaskId(previous.task_id);
        setBusy(previous.status === "running" || previous.status === "queued");
        if (previous.results)
          setCustomers((current) =>
            current.map((c) => ({
              ...c,
              ...(previous.results?.find(
                (r) => r.customer_id === c.customer_id,
              ) || {}),
            })),
          );
        if (previous.status === "failed" || previous.status === "interrupted")
          setError(
            previous.error ||
              "The previous analysis did not complete. Retry failed records to resume.",
          );
      })
      .catch((e) => setError(e.message));
  }, [authenticated]);
  useEffect(() => {
    if (!taskId || !busy) return;
    let cancelled = false;
    const poll = async () => {
      try {
        const next = await api.getTask(taskId);
        if (cancelled) return;
        setTask(next);
        if (next.status === "completed") {
          setCustomers((previous) =>
            previous.map((c) => ({
              ...c,
              ...(next.results?.find((r) => r.customer_id === c.customer_id) ||
                {}),
            })),
          );
          setSelected((current) =>
            current
              ? {
                  ...current,
                  ...(next.results?.find(
                    (r) => r.customer_id === current.customer_id,
                  ) || {}),
                }
              : null,
          );
          setBusy(false);
        } else if (next.status === "failed" || next.status === "interrupted") {
          setBusy(false);
          setError(next.error || "Analysis did not complete.");
        } else setTimeout(poll, 1000);
      } catch (e) {
        if (!cancelled) {
          setError(
            e instanceof Error ? e.message : "Could not read analysis status.",
          );
          setBusy(false);
        }
      }
    };
    poll();
    return () => {
      cancelled = true;
    };
  }, [taskId, busy]);

  const rows = useMemo(
    () =>
      customers
        .filter((c) =>
          Object.values(c)
            .join(" ")
            .toLowerCase()
            .includes(search.toLowerCase()),
        )
        .sort((a, b) => {
          const av = a[sort] || "";
          const bv = b[sort] || "";
          const n = Number(av) - Number(bv);
          const compared =
            av !== "" && bv !== "" && Number.isFinite(n)
              ? n
              : String(av).localeCompare(String(bv));
          return ascending ? compared : -compared;
        }),
    [customers, search, sort, ascending],
  );
  const overview = useMemo(() => {
    const distribution: Record<string, number> = {};
    let index = 0;
    customers.forEach((c) => {
      if (c.offer_code)
        distribution[c.offer_code] = (distribution[c.offer_code] || 0) + 1;
      index +=
        Number(c.monthly_recurring_revenue) * Number(c.churn_probability);
    });
    return { distribution, index };
  }, [customers]);

  async function onLogin(event: React.FormEvent) {
    event.preventDefault();
    setLoginError("");
    try {
      await api.login(accessCode);
      setAuthenticated(true);
      setAccessCode("");
    } catch (e) {
      setLoginError(e instanceof Error ? e.message : "Sign in failed.");
    }
  }
  async function run(mode: "mock" | "live" = "live") {
    setError("");
    setTask(null);
    setTaskId("");
    setBusy(true);
    try {
      const result = upload
        ? await api.startUploadAnalysis(upload, mode)
        : await api.startAnalysis(mode);
      setTaskId(result.task_id);
    } catch (e) {
      setBusy(false);
      setError(e instanceof Error ? e.message : "Could not start analysis.");
    }
  }
  async function onUpload(file?: File) {
    if (!file) return;
    setUpload(file);
    setUploadMessage("Validating CSV…");
    setError("");
    try {
      const result = await api.validateCsv(file);
      setCustomers(result.customers);
      setTask(null);
      setTaskId("");
      setUploadAllowed(result.analysis_allowed);
      setSyntheticData(result.synthetic_data);
      setUploadMessage(`${result.rows} rows valid. ${result.message}`);
    } catch (e) {
      setUpload(null);
      setUploadAllowed(false);
      setUploadMessage("");
      setError(e instanceof Error ? e.message : "CSV validation failed.");
    }
  }
  async function retry() {
    if (!taskId) return;
    setError("");
    try {
      await api.retryTask(taskId);
      setTask(null);
      setBusy(true);
    } catch (e) {
      setBusy(false);
      setError(e instanceof Error ? e.message : "Retry failed.");
    }
  }

  if (checking)
    return (
      <div className="center-screen">
        <div className="loader" />
      </div>
    );
  if (!authenticated)
    return (
      <main className="login-screen">
        <section className="login-card">
          <div className="brand-mark">
            <Cloud size={23} />
          </div>
          <p className="eyebrow">CLOUDCORE · PERSON 3</p>
          <h1>
            Retention
            <br />
            <span>workspace</span>
          </h1>
          <p className="muted">A private working demo for the project group.</p>
          <form onSubmit={onLogin}>
            <label htmlFor="access">Group access code</label>
            <div className="input-wrap">
              <LockKeyhole size={17} />
              <input
                id="access"
                type="password"
                value={accessCode}
                onChange={(e) => setAccessCode(e.target.value)}
                autoComplete="current-password"
                required
                placeholder="Enter your access code"
              />
            </div>
            {loginError && <p className="error-text">{loginError}</p>}
            <button className="primary full" type="submit">
              Enter workspace <ChevronRight size={17} />
            </button>
          </form>
          <p className="privacy-note">
            <ShieldCheck size={14} /> Access code stays on the server
          </p>
        </section>
        <div className="login-orbit orbit-a" />
        <div className="login-orbit orbit-b" />
      </main>
    );

  const completed = task?.status === "completed";
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            <Cloud size={20} />
          </div>
          <div>
            <strong>CloudCore</strong>
            <small>RETENTION DEMO</small>
          </div>
        </div>
        <div className="side-label">WORKSPACE</div>
        <div className="nav-item active">
          <Sparkles size={16} /> Analysis demo
        </div>
        <div className="sidebar-bottom">
          <div className="human-callout">
            <ShieldCheck size={17} />
            <div>
              <b>Human approval required</b>
              <span>Messages are drafts for review</span>
            </div>
          </div>
          <button
            className="logout"
            onClick={async () => {
              await api.logout().catch(() => {});
              setAuthenticated(false);
              setCustomers([]);
            }}
          >
            <LogOut size={15} /> Sign out
          </button>
        </div>
      </aside>
      <main className="main-content">
        <header className="topbar">
          <div>
            <span className="crumb">Workspace</span>
            <span className="slash">/</span>
            <b>Analysis demo</b>
          </div>
          <div className="top-tags">
            <span className={`tag ${syntheticData ? "green" : ""}`}>
              <span />{" "}
              {syntheticData ? "Synthetic data" : "Upload · analysis blocked"}
            </span>
            <span className="tag">V0.3 PREVIEW</span>
          </div>
        </header>
        <section className="page-heading">
          <div>
            <p className="eyebrow">RETENTION ANALYSIS</p>
            <h1>Customer overview</h1>
            <p className="muted">
              Review the synthetic customer set and generate personalised offer
              messages.
            </p>
          </div>
          <div className="heading-actions">
            <label className="button secondary upload-button">
              <FileUp size={16} /> Upload CSV
              <input
                type="file"
                accept=".csv,text/csv"
                onChange={(e) => onUpload(e.target.files?.[0])}
              />
            </label>
            <button
              className="primary"
              disabled={
                busy || !customers.length || (!!upload && !uploadAllowed)
              }
              onClick={() => run("live")}
            >
              <Sparkles size={16} />{" "}
              {busy ? "Analysis running" : "Run AI analysis"}
            </button>
          </div>
        </section>
        <div className="notice">
          <ShieldCheck size={17} />
          <span>
            {syntheticData ? (
              <>
                <b>Synthetic data only.</b> Demo records are generated for
                testing.
              </>
            ) : (
              <>
                <b>CSV validation only.</b> This file is not enabled for model
                analysis.
              </>
            )}
            Every message needs human review before use.
          </span>
        </div>
        {uploadMessage && (
          <div className="upload-status">
            <Check size={15} />
            {uploadMessage}
            <button
              onClick={() => {
                setUpload(null);
                setUploadAllowed(true);
                setSyntheticData(true);
                setUploadMessage("");
                api.getDemo().then((data) => setCustomers(data.customers));
              }}
              aria-label="Remove uploaded file"
            >
              <X size={15} />
            </button>
          </div>
        )}
        {error && (
          <div className="alert">
            <CircleAlert size={17} />
            <span>
              {error}
              {task?.failed_records?.length ? (
                <small className="failed-list">
                  {task.failed_records
                    .map((item) => `${item.customer_id}: ${item.error}`)
                    .join(" · ")}
                </small>
              ) : null}
            </span>
            {task?.status === "failed" || task?.status === "interrupted" ? (
              <button onClick={retry}>Retry failed records</button>
            ) : null}
            <button
              className="icon-button"
              onClick={() => setError("")}
              aria-label="Dismiss"
            >
              <X size={16} />
            </button>
          </div>
        )}
        {task && (
          <section className="progress-card">
            <div className="progress-top">
              <div>
                <b>
                  {completed
                    ? "Analysis complete"
                    : `Processing batch · ${task.succeeded} of ${task.total}`}
                </b>
                <span>
                  {task.failed} failed records · Offer and Reason are generated
                  locally
                </span>
              </div>
              <strong>
                {task.total
                  ? Math.round((task.succeeded / task.total) * 100)
                  : 0}
                %
              </strong>
            </div>
            <div className="progress-track">
              <div
                style={{
                  width: `${task.total ? (task.succeeded / task.total) * 100 : 0}%`,
                }}
              />
            </div>
          </section>
        )}
        {completed && (
          <section className="overview-grid">
            <div className="metric-card metric-wide">
              <div className="metric-title">
                Offer distribution <span>{task.total} CUSTOMER RECORDS</span>
              </div>
              <div className="offer-bars">
                {["O1", "O2", "O3", "O4"].map((code) => (
                  <div className="offer-bar-row" key={code}>
                    <b>{code}</b>
                    <div className="bar">
                      <i
                        style={{
                          width: `${customers.length ? ((overview.distribution[code] || 0) / customers.length) * 100 : 0}%`,
                        }}
                      />
                    </div>
                    <span>{overview.distribution[code] || 0}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="metric-card">
              <div className="metric-title">
                Risk-weighted MRR index <span>INTERNAL</span>
              </div>
              <div className="big-number">
                {new Intl.NumberFormat("en-AU", {
                  maximumFractionDigits: 0,
                }).format(task.risk_weighted_mrr_index ?? overview.index)}
              </div>
              <p>Exploratory review index · not a forecast or expected loss</p>
            </div>
          </section>
        )}
        <section className="data-card">
          <div className="table-header">
            <div>
              <h2>
                Customers <span className="count-pill">{customers.length}</span>
              </h2>
              <p>
                Eight validated input fields
                {completed ? " · analysis results available" : ""}
              </p>
            </div>
            <div className="table-tools">
              <div className="search-box">
                <Search size={16} />
                <input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search customers"
                />
              </div>
              {completed && (
                <a
                  className="button secondary download"
                  href={api.downloadUrl(taskId)}
                >
                  <ArrowDownToLine size={15} /> Export offers.csv
                </a>
              )}
            </div>
          </div>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  {columns.map(([key, label]) => (
                    <th key={key}>
                      <button
                        onClick={() => {
                          if (sort === key) setAscending(!ascending);
                          else {
                            setSort(key);
                            setAscending(true);
                          }
                        }}
                      >
                        {label}
                        <ArrowUpDown size={12} />
                      </button>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((customer) => (
                  <tr
                    key={customer.customer_id}
                    onClick={() => setSelected(customer)}
                  >
                    <td className="id-cell">{customer.customer_id}</td>
                    <td>{customer.industry}</td>
                    <td>{customer.region}</td>
                    <td>{customer.tenure_months} mo</td>
                    <td className="product-cell">{customer.products}</td>
                    <td>
                      {number(Number(customer.monthly_recurring_revenue))}
                    </td>
                    <td>
                      <span
                        className={`tier ${customer.support_tier.toLowerCase()}`}
                      >
                        {customer.support_tier}
                      </span>
                    </td>
                    <td>
                      <span className="churn-score">
                        {(Number(customer.churn_probability) * 100).toFixed(0)}%
                      </span>
                      <div className="tiny-bar">
                        <i
                          style={{
                            width: `${Number(customer.churn_probability) * 100}%`,
                          }}
                        />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!rows.length && (
              <div className="empty">No customers match your search.</div>
            )}
          </div>
          <footer className="table-footer">
            Showing {rows.length} of {customers.length} synthetic customers{" "}
            <span>Click a row to inspect details</span>
          </footer>
        </section>
        {selected && (
          <div
            className="overlay"
            onMouseDown={(e) =>
              e.target === e.currentTarget && setSelected(null)
            }
          >
            <aside className="detail-panel">
              <div className="detail-header">
                <div>
                  <span className="eyebrow">CUSTOMER DETAIL</span>
                  <h2>{selected.customer_id}</h2>
                </div>
                <button
                  className="icon-button"
                  onClick={() => setSelected(null)}
                >
                  <X size={18} />
                </button>
              </div>
              <div className="detail-content">
                <div className="detail-section">
                  <h3>Input profile</h3>
                  <div className="detail-grid">
                    {columns.slice(1).map(([key, label]) => (
                      <div key={key}>
                        <span>{label}</span>
                        <b>{selected[key]}</b>
                      </div>
                    ))}
                  </div>
                </div>
                {completed && (
                  <>
                    <div className="detail-section">
                      <h3>
                        Assigned offer{" "}
                        <span className="offer-code">
                          {selected.offer_code}
                        </span>
                      </h3>
                      <p className="offer-copy">{selected.offer}</p>
                      <p className="reason-copy">{selected.reason}</p>
                    </div>
                    <div className="detail-section message-box">
                      <h3>
                        Message <span>HUMAN REVIEW REQUIRED</span>
                      </h3>
                      <p>{selected.message || "No message available."}</p>
                    </div>
                  </>
                )}
              </div>
              <div className="detail-foot">
                <ShieldCheck size={16} /> Synthetic Data · Human Approval
                Required
              </div>
            </aside>
          </div>
        )}
      </main>
    </div>
  );
}
