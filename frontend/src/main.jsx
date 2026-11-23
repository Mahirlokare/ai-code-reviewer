import React, { useState, useEffect } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity, ArrowUpRight, Bell, Bot, CheckCircle2, ChevronDown, CircleHelp,
  Clock3, Code2, GitPullRequest, Github, LayoutDashboard, Menu, Search,
  Settings2, ShieldCheck, Sparkles, Terminal, TrendingUp, X, Zap, RefreshCw, Copy, Check
} from "lucide-react";
import "./styles.css";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

const defaultDemoPulls = [
  { id: "#284", title: "Refactor authentication middleware", repo: "acme/platform-api", author: "sarahchen", time: "12 min ago", status: "Action Required", score: 76, files: 8, additions: 146, deletions: 39, avatar: "SC" },
  { id: "#283", title: "Add caching to user endpoints", repo: "acme/platform-api", author: "marcus-dev", time: "38 min ago", status: "Reviewed", score: 94, files: 4, additions: 89, deletions: 12, avatar: "MD" },
  { id: "#282", title: "Update payment retry logic", repo: "acme/checkout", author: "jlee", time: "1 hr ago", status: "Review needed", score: 67, files: 6, additions: 201, deletions: 54, avatar: "JL" },
  { id: "#281", title: "Fix pagination edge case", repo: "acme/platform-api", author: "alexr", time: "2 hrs ago", status: "Reviewed", score: 97, files: 2, additions: 31, deletions: 6, avatar: "AR" },
];

const PRESETS = {
  "SQL Injection": `diff --git a/app/db.py b/app/db.py
@@ -10,3 +10,4 @@
 def fetch_account(user_id):
+    query = f"SELECT * FROM accounts WHERE id = '{user_id}'"
+    return cursor.execute(query)`,
  "Hardcoded Secret": `diff --git a/config/auth.py b/config/auth.py
@@ -5,3 +5,4 @@
 def init_auth():
+    api_key = "sk-ant-api03-abcdef1234567890abcdef1234567890"
+    print("Configuring auth with key")`,
  "Bare Except & Mutable Default": `diff --git a/app/worker.py b/app/worker.py
@@ -20,3 +20,6 @@
+def process_batch(items=[]):
+    try:
+        return [x * 2 for x in items]
+    except:
+        pass`,
  "Clean Code": `diff --git a/app/utils.py b/app/utils.py
@@ -1,4 +1,8 @@
+def compute_discount(subtotal: float, discount_percent: float) -> float:
+    """Compute discounted total with boundary validation."""
+    if not (0 <= discount_percent <= 100):
+        raise ValueError("Discount percent must be between 0 and 100")
+    return round(subtotal * (1 - discount_percent / 100), 2)`
};

function App() {
  const [active, setActive] = useState("Overview");
  const [apiStatus, setApiStatus] = useState("Checking");
  const [reviewText, setReviewText] = useState(PRESETS["SQL Injection"]);
  const [reviewResult, setReviewResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [reviewError, setReviewError] = useState("");
  const [showReview, setShowReview] = useState(false);
  const [search, setSearch] = useState("");
  const [mobileMenu, setMobileMenu] = useState(false);
  const [pulls, setPulls] = useState(defaultDemoPulls);
  const [metrics, setMetrics] = useState({ total_prs: 128, issues_caught: 346, time_saved: "24.6 hrs", accuracy: "95.2%" });
  const [copiedIdx, setCopiedIdx] = useState(null);

  const nav = [
    { label: "Overview", icon: LayoutDashboard },
    { label: "Pull Requests", icon: GitPullRequest },
    { label: "Review Playground", icon: Code2 },
    { label: "Analytics", icon: TrendingUp }
  ];

  const fetchLiveState = () => {
    fetch(API_BASE + "/health")
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(() => {
        setApiStatus("Online");
        // Fetch live PRs
        fetch(API_BASE + "/api/v1/pull-requests")
          .then(r => r.ok ? r.json() : Promise.reject())
          .then(data => { if (data && data.length) setPulls(data); })
          .catch(() => {});
        // Fetch live metrics
        fetch(API_BASE + "/api/v1/metrics")
          .then(r => r.ok ? r.json() : Promise.reject())
          .then(m => {
            setMetrics({
              total_prs: m.total_pull_requests || 128,
              issues_caught: m.total_findings || 346,
              time_saved: `${((m.total_pull_requests || 12) * 1.5).toFixed(1)} hrs`,
              accuracy: `${m.average_quality_score || 95}%`
            });
          })
          .catch(() => {});
      })
      .catch(() => setApiStatus("Offline"));
  };

  useEffect(() => {
    fetchLiveState();
    const interval = setInterval(fetchLiveState, 15000);
    return () => clearInterval(interval);
  }, []);

  const runReview = async () => {
    setBusy(true);
    setReviewError("");
    setReviewResult(null);
    try {
      const res = await fetch(API_BASE + "/api/v1/reviews", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ diff: reviewText, language: "python", repository: "demo/playground" })
      });
      if (!res.ok) throw new Error("Review API responded with status " + res.status);
      const data = await res.json();
      setReviewResult(data);
      fetchLiveState();
    } catch (e) {
      setReviewError(e.message + ". Backend URL: " + API_BASE);
    } finally {
      setBusy(false);
    }
  };

  const copySuggestion = (text, idx) => {
    navigator.clipboard.writeText(text);
    setCopiedIdx(idx);
    setTimeout(() => setCopiedIdx(null), 2000);
  };

  const filtered = pulls.filter(p => (p.title + p.repo + p.author).toLowerCase().includes(search.toLowerCase()));
  const go = (label) => {
    setActive(label);
    setMobileMenu(false);
    if (label === "Review Playground") setShowReview(true);
  };

  return (
    <div className="app-shell">
      <aside className={"sidebar " + (mobileMenu ? "mobile-open" : "")}>
        <div className="brand">
          <div className="brand-mark"><Bot size={21}/></div>
          <div><strong>ReviewPilot</strong><small>AI code intelligence</small></div>
          <button className="close-menu" onClick={() => setMobileMenu(false)}><X/></button>
        </div>
        <div className="workspace">
          <div className="workspace-avatar">A</div>
          <div><b>Acme Engineering</b><small>Workspace</small></div>
          <ChevronDown size={15}/>
        </div>
        <div className="nav-label">WORKSPACE</div>
        {nav.map(n => (
          <button key={n.label} className={"nav-item " + (active === n.label ? "selected" : "")} onClick={() => go(n.label)}>
            <n.icon size={18}/>
            <span>{n.label}</span>
            {n.label === "Pull Requests" && <span className="nav-count">{pulls.length}</span>}
          </button>
        ))}
        <div className="nav-label integrations-label">INTEGRATIONS</div>
        <button className="nav-item">
          <Github size={18}/>
          <span>GitHub webhook</span>
          <span className={"connected-dot " + (apiStatus === "Online" ? "active" : "")}/>
        </button>
        <button className="nav-item">
          <ShieldCheck size={18}/>
          <span>Multi-agent scans</span>
        </button>
        <div className="sidebar-bottom">
          <div className="plan-card">
            <div className="plan-top"><Sparkles size={15}/> <b>ReviewPilot Pro</b></div>
            <p>Autonomous multi-agent review pipeline active.</p>
            <button onClick={() => window.open("https://github.com/Mahirlokare/ai-code-reviewer", "_blank")}>
              GitHub Repo <ArrowUpRight size={14}/>
            </button>
          </div>
          <div className="profile">
            <div className="profile-avatar">ML</div>
            <div><b>Mahir Lokare</b><small>Developer</small></div>
            <Settings2 size={17}/>
          </div>
        </div>
      </aside>

      {mobileMenu && <div className="overlay" onClick={() => setMobileMenu(false)}/>}

      <main className="main">
        <header className="topbar">
          <button className="hamburger" onClick={() => setMobileMenu(true)}><Menu/></button>
          <div className="breadcrumbs">Workspace <span>/</span> <b>{active}</b></div>
          <div className="top-actions">
            <div className="api-pill" onClick={fetchLiveState} style={{cursor: "pointer"}} title="Click to refresh status">
              <span className={"status-dot " + (apiStatus === "Online" ? "green" : apiStatus === "Offline" ? "red" : "")}/>
              {apiStatus === "Online" ? "Backend connected" : apiStatus === "Offline" ? "Backend offline" : "Checking…"}
            </div>
            <button className="icon-btn" title="Refresh" onClick={fetchLiveState}><RefreshCw size={16}/></button>
            <div className="top-avatar">ML</div>
          </div>
        </header>

        <div className="content">
          <div className="welcome-row">
            <div>
              <div className="eyebrow"><Sparkles size={14}/> MULTI-AGENT CODE INTELLIGENCE</div>
              <h1>Welcome, Mahir <span className="wave">✦</span></h1>
              <p className="subtitle">Real-time review pipeline for GitHub PRs, Static Analysis, and Security audits.</p>
            </div>
            <button className="primary-btn" onClick={() => { setActive("Review Playground"); setShowReview(true); }}>
              <Zap size={16}/> Run a code review
            </button>
          </div>

          <div className="metrics-grid">
            <Metric icon={<GitPullRequest/>} label="Pull requests analyzed" value={metrics.total_prs} change="+24.2%" caption="all-time" color="blue"/>
            <Metric icon={<ShieldCheck/>} label="Issues detected" value={metrics.issues_caught} change="+16.1%" caption="total findings" color="purple"/>
            <Metric icon={<Clock3/>} label="Developer hours saved" value={metrics.time_saved} change="+12.4 hrs" caption="estimated" color="mint"/>
            <Metric icon={<Activity/>} label="Quality index" value={metrics.accuracy} change="+3.2%" caption="pass rate" color="orange"/>
          </div>

          <section className="panel pr-panel">
            <div className="panel-header">
              <div>
                <h2>Live Pull Requests</h2>
                <p>Audited changes processed by webhook and API</p>
              </div>
              <div className="table-tools">
                <div className="searchbox">
                  <Search size={15}/>
                  <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Filter pull requests..."/>
                </div>
              </div>
            </div>
            <div className="pr-table">
              <div className="pr-table-head">
                <span>Pull request</span>
                <span>Quality Score</span>
                <span>Status</span>
                <span>Analyzed</span>
              </div>
              {filtered.map(pr => (
                <div className="pr-row" key={pr.id}>
                  <div className="pr-title">
                    <div className="pr-icon"><GitPullRequest size={16}/></div>
                    <div>
                      <b>{pr.title}</b>
                      <small>{pr.repo} · {pr.id} · by {pr.author}</small>
                    </div>
                  </div>
                  <div className="score">
                    <div className="score-ring" style={{ "--score": pr.score }}>
                      <span>{pr.score}</span>
                    </div>
                  </div>
                  <div>
                    <span className={"status-tag " + (pr.status === "Reviewed" ? "reviewed" : "needed")}>
                      {pr.status === "Reviewed" ? <CheckCircle2 size={13}/> : <Clock3 size={13}/>} {pr.status}
                    </span>
                  </div>
                  <div className="updated">{pr.time}</div>
                </div>
              ))}
            </div>
            <div className="panel-footer">
              Showing {filtered.length} pull requests
              <button onClick={() => window.open("https://github.com/Mahirlokare/ai-code-reviewer", "_blank")}>
                View GitHub Repository <ArrowUpRight size={14}/>
              </button>
            </div>
          </section>

          <div className="bottom-grid">
            <section className="panel findings-panel">
              <div className="panel-header">
                <div>
                  <h2>Active Rule Presets</h2>
                  <p>Click any rule to load and test in playground</p>
                </div>
              </div>
              {Object.keys(PRESETS).map(name => (
                <div
                  className="finding-row"
                  key={name}
                  style={{ cursor: "pointer" }}
                  onClick={() => {
                    setReviewText(PRESETS[name]);
                    setShowReview(true);
                  }}
                >
                  <span className="severity critical"/>
                  <div>
                    <b>{name}</b>
                    <small>Click to load diff and run multi-agent inspection</small>
                  </div>
                  <span className="severity-label high">Test</span>
                </div>
              ))}
            </section>

            <section className="panel engine-panel">
              <div className="panel-header">
                <div>
                  <h2>Review Engine Subsystems</h2>
                  <p>Multi-agent LangGraph architecture</p>
                </div>
                <span className="live-tag"><i/> 100% OPERATIONAL</span>
              </div>
              <div className="engine-status">
                <div className="engine-icon green"><ShieldCheck size={23}/></div>
                <div><b>Security Agent</b><small>OWASP Top 10, Secrets & Injection checks</small></div>
                <span className="online-tag">Active</span>
              </div>
              <div className="engine-status">
                <div className="engine-icon"><Bot size={23}/></div>
                <div><b>Static Analysis Agent</b><small>Exceptions, null dereferences, resource leaks</small></div>
                <span className="online-tag">Active</span>
              </div>
              <div className="engine-status">
                <div className="engine-icon violet"><Sparkles size={23}/></div>
                <div><b>Style & Architecture Agent</b><small>Idomatic conventions & layer boundary checks</small></div>
                <span className="online-tag">Active</span>
              </div>
              <div className="engine-note">
                <Terminal size={14}/> Live backend connected to <code>{API_BASE}</code>
              </div>
            </section>
          </div>

          <footer>
            © 2026 ReviewPilot · AI Code Reviewer ·
            <a href="https://github.com/Mahirlokare/ai-code-reviewer" target="_blank" rel="noreferrer">
              GitHub repository <ArrowUpRight size={13}/>
            </a>
          </footer>
        </div>
      </main>

      {showReview && (
        <div className="modal-backdrop" onClick={e => { if (e.target === e.currentTarget) setShowReview(false); }}>
          <div className="review-modal">
            <div className="modal-head">
              <div>
                <span className="eyebrow"><Sparkles size={13}/> MULTI-AGENT REVIEW PLAYGROUND</span>
                <h2>Inspect Code Changes</h2>
              </div>
              <button className="icon-btn" onClick={() => setShowReview(false)}><X/></button>
            </div>
            <p className="modal-desc">Select a preset or paste any git diff. The multi-agent pipeline analyzes security, correctness, and style concurrently.</p>

            <div style={{ display: "flex", gap: "8px", marginBottom: "12px", flexWrap: "wrap" }}>
              {Object.keys(PRESETS).map(name => (
                <button
                  key={name}
                  className="select-btn"
                  style={{ fontSize: "11px", padding: "4px 8px" }}
                  onClick={() => setReviewText(PRESETS[name])}
                >
                  {name}
                </button>
              ))}
            </div>

            <textarea
              className="code-input"
              value={reviewText}
              onChange={e => setReviewText(e.target.value)}
              spellCheck="false"
              rows={10}
            />

            <div className="modal-controls">
              <span className="api-hint">
                <span className={"status-dot " + (apiStatus === "Online" ? "green" : "red")}/>
                {apiStatus === "Online" ? "Connected to backend API" : "Backend offline (Start uvicorn on port 8000)"}
              </span>
              <button className="primary-btn" disabled={busy || !reviewText.trim()} onClick={runReview}>
                {busy ? <><Activity size={16}/> Reviewing with agents…</> : <><Zap size={16}/> Run Multi-Agent Review</>}
              </button>
            </div>

            {reviewError && <div className="error-box">{reviewError}</div>}

            {reviewResult && (
              <div className="review-output">
                <div className="result-head">
                  <b>Review Synthesis ({reviewResult.engine})</b>
                  <span>{reviewResult.findings.length} finding(s)</span>
                </div>
                <div style={{ whiteSpace: "pre-wrap", fontSize: "13px", color: "#334155", margin: "10px 0" }}>
                  {reviewResult.summary}
                </div>
                {reviewResult.findings.map((f, i) => (
                  <div className="result-finding" key={i}>
                    <span className={"severity " + f.severity}/>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                        <b>{f.title}</b>
                        <span className={"severity-label " + f.severity}>{f.severity}</span>
                        {f.agent && <span style={{ fontSize: "10px", background: "#f1f5f9", padding: "2px 6px", borderRadius: "4px", color: "#475569" }}>Agent: {f.agent}</span>}
                      </div>
                      <small>
                        {f.file_path || "File"} {f.line ? `· Line ${f.line}` : ""} · confidence {(f.confidence * 100).toFixed(0)}%
                      </small>
                      <p>{f.description}</p>
                      {f.suggestion && (
                        <div style={{ marginTop: "6px", background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "4px", padding: "8px", position: "relative" }}>
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                            <small style={{ fontWeight: 600, color: "#2563eb" }}>Suggested Diff Fix:</small>
                            <button
                              onClick={() => copySuggestion(f.suggestion, i)}
                              style={{ background: "none", border: "none", cursor: "pointer", display: "flex", alignItems: "center", gap: "4px", fontSize: "11px", color: "#64748b" }}
                            >
                              {copiedIdx === i ? <><Check size={12} color="green"/> Copied</> : <><Copy size={12}/> Copy</>}
                            </button>
                          </div>
                          <pre style={{ margin: 0, padding: "4px", fontSize: "12px", background: "#ffffff", border: "1px solid #e2e8f0", borderRadius: "3px" }}>
                            <code>{f.suggestion}</code>
                          </pre>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function Metric({ icon, label, value, change, caption, color }) {
  return (
    <div className="metric-card">
      <div className={"metric-icon " + color}>{icon}</div>
      <div className="metric-label">{label}</div>
      <div className="metric-value">{value}</div>
      <div className="metric-change"><span>{change}</span> <small>{caption}</small></div>
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App/>);
