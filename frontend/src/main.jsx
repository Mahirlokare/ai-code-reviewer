import React, { useState, useEffect } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity, ArrowUpRight, Bell, Bot, CheckCircle2, ChevronDown, CircleHelp,
  Clock3, Code2, GitPullRequest, Github, LayoutDashboard, Menu, Search,
  Settings2, ShieldCheck, Sparkles, Terminal, TrendingUp, X, Zap, RefreshCw,
  Copy, Check, FileText, Globe, Play, Layers, AlertTriangle, Info, ShieldAlert
} from "lucide-react";
import "./styles.css";

const formatApiBase = (raw) => {
  if (!raw) return "https://ai-code-reviewer-api-z7hr.onrender.com";
  let base = raw.trim();
  if (base.startsWith("/")) return base;
  if (!base.startsWith("http://") && !base.startsWith("https://")) {
    if (!base.includes(".")) {
      base = `https://${base}.onrender.com`;
    } else {
      base = `https://${base}`;
    }
  }
  return base.replace(/\/+$/, "");
};

const API_BASE = formatApiBase(import.meta.env.VITE_API_BASE);

const MULTI_LANG_PRESETS = {
  python: {
    label: "Python",
    ext: "py",
    sample: `def query_user_records(user_id, status_filter=[]):
    # Potential SQL injection via string formatting
    query = f"SELECT id, name, role FROM users WHERE id = '{user_id}'"
    print("Executing query for user: " + str(user_id))
    try:
        results = db.cursor.execute(query)
        return results.fetchall()
    except:
        pass`
  },
  javascript: {
    label: "JavaScript / TypeScript",
    ext: "js",
    sample: `function authenticateUser(req, res) {
    const { token, role } = req.body;
    // Loose equality performs implicit type coercion
    if (token == "demo-token") {
        console.log("Logged in as: " + role);
        return res.json({ success: true });
    }
    // Command execution with untrusted input
    const child = require("child_process");
    child.exec("ping -c 1 " + req.query.host);
}`
  },
  go: {
    label: "Go (Golang)",
    ext: "go",
    sample: `package main

import (
    "fmt"
    "os"
)

func ReadConfig(path string) error {
    file, err := os.Open(path)
    // Defer inside loop only runs when surrounding function returns
    for i := 0; i < 5; i++ {
        defer file.Close()
    }
    // Ignoring error return with blank identifier
    _, _ = file.Stat()
    fmt.Println("Config loaded")
    return nil
}`
  },
  rust: {
    label: "Rust",
    ext: "rs",
    sample: `pub fn process_order(order_id: Option<u64>) -> u64 {
    // Direct unwrap will panic thread if Option is None
    let id = order_id.unwrap();
    println!("Processing order: {}", id);
    id * 2
}`
  },
  java: {
    label: "Java",
    ext: "java",
    sample: `public class UserService {
    public boolean checkRole(String role, String inputQuery) {
        // String reference equality with == instead of .equals()
        if (role == "ADMIN") {
            System.out.println("Admin access granted");
        }
        // Raw SQL query concatenation
        String sql = "SELECT * FROM accounts WHERE name = '" + inputQuery + "'";
        return true;
    }
}`
  },
  c_cpp: {
    label: "C / C++",
    ext: "cpp",
    sample: `void copy_buffer(const char *untrusted_input) {
    char local_buffer[32];
    // Unbounded strcpy can overflow stack buffer
    strcpy(local_buffer, untrusted_input);
    printf("Copied buffer: %s\\n", local_buffer);
}`
  },
  shell: {
    label: "Shell / Bash",
    ext: "sh",
    sample: `#!/bin/bash
TARGET_DIR=$1
# Unquoted variable expansion in recursive delete
rm -rf $TARGET_DIR/cache
# Piping unverified remote script directly into bash
curl -s https://example.com/install.sh | bash`
  },
  dockerfile: {
    label: "Dockerfile",
    ext: "Dockerfile",
    sample: `FROM ubuntu:22.04
# Container running as privileged root user
USER root
COPY . /app
CMD ["python3", "/app/main.py"]`
  }
};

const defaultDemoPulls = [
  {
    id: "#284",
    title: "Refactor authentication middleware",
    repo: "acme/platform-api",
    author: "sarahchen",
    time: "12 min ago",
    status: "Action Required",
    score: 76,
    files: 2,
    additions: 146,
    deletions: 0,
    avatar: "SC",
    summary: "🚨 Critical security vulnerability detected in auth handler.\n\nMulti-Agent Findings Breakdown:\n- 🔴 Critical: 1\n- 🟡 Medium: 1\n\nAll findings synthesized across Security and Static Analysis agents.",
    findings: [
      {
        severity: "critical",
        category: "security",
        agent: "security",
        title: "Potential hard-coded credential",
        description: "Detected API token assignment in auth config.",
        line: 42,
        file_path: "config/auth.py",
        confidence: 0.95,
        suggestion: "api_key = os.environ.get('AUTH_SECRET')"
      },
      {
        severity: "medium",
        category: "correctness",
        agent: "static_analysis",
        title: "Broad bare exception handler",
        description: "Bare except clause catches all exceptions including system interrupts.",
        line: 108,
        file_path: "services/session.py",
        confidence: 0.88,
        suggestion: "except AuthenticationError as err:\n    logger.warning(err)"
      }
    ]
  },
  {
    id: "#283",
    title: "Add caching to user endpoints",
    repo: "acme/platform-api",
    author: "marcus-dev",
    time: "38 min ago",
    status: "Reviewed",
    score: 94,
    files: 1,
    additions: 89,
    deletions: 0,
    avatar: "MD",
    summary: "✅ Clean review. Minor clean-code suggestions.\n\nMulti-Agent Findings Breakdown:\n- 🔵 Low: 1\n\nSynthesized across Style Agent.",
    findings: [
      {
        severity: "low",
        category: "debugging",
        agent: "style",
        title: "Leftover debug statement",
        description: "Found print statement in cache worker.",
        line: 16,
        file_path: "handlers/login.py",
        confidence: 0.75,
        suggestion: "logger.debug('Cache populated')"
      }
    ]
  }
];

function App() {
  const [activeTab, setActiveTab] = useState("Overview");
  const [apiStatus, setApiStatus] = useState("Checking");
  const [pulls, setPulls] = useState(defaultDemoPulls);
  const [metrics, setMetrics] = useState({ total_prs: 128, issues_caught: 346, time_saved: "24.6 hrs", accuracy: "95.2%" });
  const [search, setSearch] = useState("");
  const [mobileMenu, setMobileMenu] = useState(false);
  const [selectedPr, setSelectedPr] = useState(null);
  const [copiedIdx, setCopiedIdx] = useState(null);

  // Direct Code Runner State
  const [selectedLang, setSelectedLang] = useState("python");
  const [codeSnippet, setCodeSnippet] = useState(MULTI_LANG_PRESETS["python"].sample);
  const [codeReviewResult, setCodeReviewResult] = useState(null);
  const [codeBusy, setCodeBusy] = useState(false);
  const [codeError, setCodeError] = useState("");

  // Review Any Repo State
  const [repoUrlInput, setRepoUrlInput] = useState("https://github.com/Mahirlokare/ai-code-reviewer");
  const [repoBusy, setRepoBusy] = useState(false);
  const [repoError, setRepoError] = useState("");
  const [repoSuccess, setRepoSuccess] = useState("");
  const [repoReviewResult, setRepoReviewResult] = useState(null);

  // Global Quick Review Modal State
  const [showQuickModal, setShowQuickModal] = useState(false);
  const [quickDiff, setQuickDiff] = useState(MULTI_LANG_PRESETS["python"].sample);
  const [quickResult, setQuickResult] = useState(null);
  const [quickBusy, setQuickBusy] = useState(false);
  const [quickError, setQuickError] = useState("");

  const fetchLiveState = () => {
    fetch(API_BASE + "/health")
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(() => {
        setApiStatus("Online");
        fetch(API_BASE + "/api/v1/pull-requests")
          .then(r => r.ok ? r.json() : Promise.reject())
          .then(data => { if (data && data.length) setPulls(data); })
          .catch(() => {});
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

  const handleLanguageChange = (langKey) => {
    setSelectedLang(langKey);
    setCodeSnippet(MULTI_LANG_PRESETS[langKey].sample);
    setCodeReviewResult(null);
    setCodeError("");
  };

  const runDirectCodeAnalysis = async () => {
    setCodeBusy(true);
    setCodeError("");
    setCodeReviewResult(null);
    try {
      const res = await fetch(API_BASE + "/api/v1/code/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          code: codeSnippet,
          language: selectedLang,
          filename: `snippet.${MULTI_LANG_PRESETS[selectedLang].ext}`
        })
      });
      if (!res.ok) throw new Error("API returned status " + res.status);
      const data = await res.json();
      setCodeReviewResult(data);
    } catch (e) {
      setCodeError(e.message + ". Make sure backend is active at " + API_BASE);
    } finally {
      setCodeBusy(false);
    }
  };

  const handleFetchAnyRepo = async () => {
    if (!repoUrlInput.trim()) return;
    setRepoBusy(true);
    setRepoError("");
    setRepoSuccess("");
    setRepoReviewResult(null);
    try {
      const res = await fetch(API_BASE + "/api/v1/repos/fetch-and-review", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo_url_or_slug: repoUrlInput })
      });
      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || "Failed to fetch repository from GitHub");
      }
      const data = await res.json();
      setRepoReviewResult(data);
      setRepoSuccess(`Successfully reviewed ${data.pull_request}! Quality score: ${data.score}/100.`);
      fetchLiveState();
    } catch (e) {
      setRepoError(e.message);
    } finally {
      setRepoBusy(false);
    }
  };

  const copySuggestion = (text, idx) => {
    navigator.clipboard.writeText(text);
    setCopiedIdx(idx);
    setTimeout(() => setCopiedIdx(null), 2000);
  };

  const filteredPulls = pulls.filter(p =>
    (p.title + p.repo + p.author).toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="app-shell">
      <aside className={"sidebar " + (mobileMenu ? "mobile-open" : "")}>
        <div className="brand">
          <div className="brand-mark"><Bot size={21}/></div>
          <div><strong>ReviewPilot</strong><small>Humanized AI code review</small></div>
          <button className="close-menu" onClick={() => setMobileMenu(false)}><X/></button>
        </div>

        <div className="workspace">
          <div className="workspace-avatar">ML</div>
          <div><b>Mahir Lokare</b><small>Active Workspace</small></div>
          <ChevronDown size={15}/>
        </div>

        <div className="nav-label">NAVIGATION</div>
        <button
          className={"nav-item " + (activeTab === "Overview" ? "selected" : "")}
          onClick={() => { setActiveTab("Overview"); setMobileMenu(false); }}
        >
          <LayoutDashboard size={18}/>
          <span>Overview</span>
        </button>

        <button
          className={"nav-item " + (activeTab === "CodeRunner" ? "selected" : "")}
          onClick={() => { setActiveTab("CodeRunner"); setMobileMenu(false); }}
        >
          <Code2 size={18}/>
          <span>Direct Code Runner</span>
          <span className="nav-tab-badge">Any Lang</span>
        </button>

        <button
          className={"nav-item " + (activeTab === "ReviewRepo" ? "selected" : "")}
          onClick={() => { setActiveTab("ReviewRepo"); setMobileMenu(false); }}
        >
          <Globe size={18}/>
          <span>Review Any Repo</span>
          <span className="nav-tab-badge">GitHub</span>
        </button>

        <button
          className={"nav-item " + (activeTab === "PullRequests" ? "selected" : "")}
          onClick={() => { setActiveTab("PullRequests"); setMobileMenu(false); }}
        >
          <GitPullRequest size={18}/>
          <span>Pull Requests</span>
          <span className="nav-count">{pulls.length}</span>
        </button>

        <div className="nav-label integrations-label">SUBSYSTEM STATUS</div>
        <div className="engine-status" style={{ padding: "8px 10px", border: "none" }}>
          <div className="engine-icon green" style={{ width: 24, height: 24 }}><ShieldCheck size={14}/></div>
          <div><b style={{ fontSize: "11px" }}>Security & OWASP</b><small>15+ Languages</small></div>
          <span className="online-tag">Active</span>
        </div>
        <div className="engine-status" style={{ padding: "8px 10px", border: "none" }}>
          <div className="engine-icon" style={{ width: 24, height: 24 }}><Bot size={14}/></div>
          <div><b style={{ fontSize: "11px" }}>Static Analysis</b><small>Bugs & Leaks</small></div>
          <span className="online-tag">Active</span>
        </div>

        <div className="sidebar-bottom">
          <div className="plan-card">
            <div className="plan-top"><Sparkles size={15}/> <b>ReviewPilot Engine</b></div>
            <p>Universal multi-agent reviewer active across all languages and platforms.</p>
            <button onClick={() => window.open("https://github.com/Mahirlokare/ai-code-reviewer", "_blank")}>
              GitHub Repository <ArrowUpRight size={14}/>
            </button>
          </div>
          <div className="profile">
            <div className="profile-avatar">ML</div>
            <div><b>Mahir Lokare</b><small>Lead Engineer</small></div>
            <Settings2 size={17}/>
          </div>
        </div>
      </aside>

      {mobileMenu && <div className="overlay" onClick={() => setMobileMenu(false)}/>}

      <main className="main">
        <header className="topbar">
          <button className="hamburger" onClick={() => setMobileMenu(true)}><Menu/></button>
          <div className="breadcrumbs">
            ReviewPilot <span>/</span> <b>{activeTab}</b>
          </div>
          <div className="top-actions">
            <div className="api-pill" onClick={fetchLiveState} style={{ cursor: "pointer" }} title="Click to refresh connection">
              <span className={"status-dot " + (apiStatus === "Online" ? "green" : apiStatus === "Offline" ? "red" : "")}/>
              {apiStatus === "Online" ? "Backend connected (Port 8000)" : apiStatus === "Offline" ? "Backend offline" : "Checking…"}
            </div>
            <button className="icon-btn" title="Refresh data" onClick={fetchLiveState}><RefreshCw size={16}/></button>
            <div className="top-avatar">ML</div>
          </div>
        </header>

        <div className="content">
          {/* TAB 1: OVERVIEW */}
          {activeTab === "Overview" && (
            <>
              <div className="welcome-row">
                <div>
                  <div className="eyebrow"><Sparkles size={14}/> HUMANIZED AI CODE REVIEWER</div>
                  <h1>Welcome, Mahir <span className="wave">✦</span></h1>
                  <p className="subtitle">
                    Autonomous code intelligence that provides friendly, actionable feedback on security, correctness, and architecture.
                  </p>
                </div>
                <div style={{ display: "flex", gap: "10px" }}>
                  <button className="primary-btn" onClick={() => setActiveTab("CodeRunner")}>
                    <Play size={16}/> Direct Code Runner
                  </button>
                  <button className="primary-btn" style={{ background: "linear-gradient(135deg, #1e3a8a, #2563eb)" }} onClick={() => setActiveTab("ReviewRepo")}>
                    <Globe size={16}/> Review Any Repo
                  </button>
                </div>
              </div>

              <div className="metrics-grid">
                <Metric icon={<GitPullRequest/>} label="Pull requests audited" value={metrics.total_prs} change="+24.2%" caption="all-time" color="blue"/>
                <Metric icon={<ShieldCheck/>} label="Issues detected" value={metrics.issues_caught} change="+16.1%" caption="total findings" color="purple"/>
                <Metric icon={<Clock3/>} label="Developer hours saved" value={metrics.time_saved} change="+12.4 hrs" caption="estimated" color="mint"/>
                <Metric icon={<Activity/>} label="Code quality score" value={metrics.accuracy} change="+3.2%" caption="average" color="orange"/>
              </div>

              <section className="panel pr-panel">
                <div className="panel-header">
                  <div>
                    <h2>Recent Audited Pull Requests</h2>
                    <p>Click any row to inspect line-level findings, executive summary, and one-click fixes</p>
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
                    <span>Review Status</span>
                    <span>Updated</span>
                  </div>
                  {filteredPulls.map(pr => (
                    <div
                      className="pr-row"
                      key={pr.id}
                      style={{ cursor: "pointer" }}
                      onClick={() => setSelectedPr(pr)}
                      title="Click to view detailed report"
                    >
                      <div className="pr-title">
                        <div className="pr-icon"><GitPullRequest size={16}/></div>
                        <div>
                          <b>{pr.title}</b>
                          <small>{pr.repo} · {pr.id} · by @{pr.author}</small>
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
                  Showing {filteredPulls.length} audited pull requests · Click any row to inspect report
                  <button onClick={() => setActiveTab("ReviewRepo")}>
                    Analyze new repo <ArrowUpRight size={14}/>
                  </button>
                </div>
              </section>
            </>
          )}

          {/* TAB 2: DIRECT CODE RUNNER (EVERY LANGUAGE) */}
          {activeTab === "CodeRunner" && (
            <div>
              <div className="welcome-row">
                <div>
                  <div className="eyebrow"><Code2 size={14}/> DIRECT CODE RUNNER & MULTI-LANGUAGE REVIEWER</div>
                  <h1>Direct Code Playground</h1>
                  <p className="subtitle">
                    Paste raw source code in any language to execute multi-agent security, bug, and performance inspection.
                  </p>
                </div>
                <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
                  <label style={{ fontSize: "12px", color: "#8da2bc" }}>Language:</label>
                  <select
                    className="lang-select"
                    value={selectedLang}
                    onChange={e => handleLanguageChange(e.target.value)}
                  >
                    {Object.keys(MULTI_LANG_PRESETS).map(k => (
                      <option key={k} value={k}>{MULTI_LANG_PRESETS[k].label}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="code-runner-grid">
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                    <small style={{ color: "#7f94af", fontWeight: 600 }}>SOURCE CODE EDITOR:</small>
                    <button
                      className="text-btn"
                      onClick={() => setCodeSnippet(MULTI_LANG_PRESETS[selectedLang].sample)}
                    >
                      Reset to sample preset
                    </button>
                  </div>
                  <textarea
                    className="code-input"
                    style={{ height: "480px", fontFamily: "'JetBrains Mono', Consolas, monospace", fontSize: "13px" }}
                    value={codeSnippet}
                    onChange={e => setCodeSnippet(e.target.value)}
                    spellCheck="false"
                  />
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "12px" }}>
                    <small style={{ color: "#6e84a3" }}>Supports Python, JS/TS, Go, Rust, Java, C/C++, Shell, Dockerfile, SQL</small>
                    <button
                      className="primary-btn"
                      disabled={codeBusy || !codeSnippet.trim()}
                      onClick={runDirectCodeAnalysis}
                    >
                      {codeBusy ? <><Activity size={16}/> Analyzing across agents…</> : <><Zap size={16}/> Analyze & Review Code</>}
                    </button>
                  </div>
                  {codeError && <div className="error-box" style={{ marginTop: "12px" }}>{codeError}</div>}
                </div>

                <div>
                  <small style={{ color: "#7f94af", fontWeight: 600 }}>HUMANIZED REVIEW REPORT:</small>
                  {codeReviewResult ? (
                    <div style={{ marginTop: "8px" }}>
                      <div className="human-feedback-card">
                        <div className="human-feedback-header">
                          <CheckCircle2 size={18} color="#40c6a5"/>
                          <span>Executive Review Synthesis</span>
                        </div>
                        <div style={{ whiteSpace: "pre-wrap", fontSize: "12.5px", color: "#cbd9ec", lineHeight: 1.6 }}>
                          {codeReviewResult.summary}
                        </div>
                      </div>

                      <div style={{ maxHeight: "380px", overflowY: "auto" }}>
                        {codeReviewResult.findings.map((f, i) => (
                          <div className="result-finding" key={i} style={{ background: "#111c2c", padding: "12px", borderRadius: "8px", marginBottom: "10px", border: "1px solid #23344a" }}>
                            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                              <span className={"tag-pill " + f.severity}>{f.severity}</span>
                              <b style={{ fontSize: "12px", color: "#e2ecf8" }}>{f.title}</b>
                              {f.agent && <span style={{ fontSize: "10px", background: "#1a2c42", padding: "2px 6px", borderRadius: "4px", color: "#7eaee9" }}>{f.agent}</span>}
                            </div>
                            <small style={{ color: "#7e93af", display: "block", marginBottom: "6px" }}>
                              Line {f.line || "—"} · confidence {((f.confidence || 0.85) * 100).toFixed(0)}%
                            </small>
                            <p style={{ fontSize: "11.5px", color: "#a5b9d3", margin: "4px 0 8px" }}>{f.description}</p>
                            {f.suggestion && (
                              <div style={{ background: "#0a1320", border: "1px solid #1f2f45", borderRadius: "6px", padding: "8px" }}>
                                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                                  <small style={{ color: "#60a5fa", fontWeight: 600 }}>Humanized Suggestion Fix:</small>
                                  <button
                                    onClick={() => copySuggestion(f.suggestion, `code-${i}`)}
                                    style={{ background: "none", border: "none", color: "#7992b2", cursor: "pointer", display: "flex", alignItems: "center", gap: "4px", fontSize: "11px" }}
                                  >
                                    {copiedIdx === `code-${i}` ? <><Check size={12} color="green"/> Copied</> : <><Copy size={12}/> Copy fix</>}
                                  </button>
                                </div>
                                <pre style={{ margin: 0, padding: "4px", fontSize: "11.5px", color: "#93c5fd" }}>
                                  <code>{f.suggestion}</code>
                                </pre>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <div style={{ marginTop: "8px", border: "1px dashed #22344c", borderRadius: "8px", padding: "40px 20px", textAlign: "center", color: "#6f839e" }}>
                      <Bot size={34} style={{ marginBottom: "10px", color: "#4f7cae" }}/>
                      <p>Ready to analyze. Select a language on the left or paste your code snippet, then click <b>Analyze & Review Code</b>.</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: REVIEW ANY REPOSITORY */}
          {activeTab === "ReviewRepo" && (
            <div>
              <div className="welcome-row">
                <div>
                  <div className="eyebrow"><Globe size={14}/> UNIVERSAL REPOSITORY CONNECTOR</div>
                  <h1>Review Any Public Repository</h1>
                  <p className="subtitle">
                    Enter any public GitHub URL — full repository (e.g. 'https://github.com/Mahirlokare/ai-code-reviewer'), PR link (/pull/1), commit (/commit/abc), file (/blob/main/...), or slug ('owner/repo') — to run the multi-agent review pipeline live.
                  </p>
                </div>
              </div>

              <div className="panel" style={{ padding: "24px", marginBottom: "20px" }}>
                <label style={{ fontSize: "12px", color: "#8ca0b8", fontWeight: 600 }}>ENTER GITHUB URL OR REPO SLUG:</label>
                <div className="repo-input-bar">
                  <input
                    className="repo-input"
                    value={repoUrlInput}
                    onChange={e => setRepoUrlInput(e.target.value)}
                    placeholder="https://github.com/Mahirlokare/ai-code-reviewer or owner/repo/pull/123 or owner/repo"
                  />
                  <button
                    className="primary-btn"
                    disabled={repoBusy || !repoUrlInput.trim()}
                    onClick={handleFetchAnyRepo}
                  >
                    {repoBusy ? <><Activity size={16}/> Analyzing GitHub code…</> : <><Globe size={16}/> Fetch & Review Code</>}
                  </button>
                </div>

                {repoError && <div className="error-box" style={{ marginBottom: "14px" }}>{repoError}</div>}
                {repoSuccess && (
                  <div style={{ background: "#11382d", border: "1px solid #236f5b", color: "#74e2c0", padding: "12px 16px", borderRadius: "8px", marginBottom: "14px" }}>
                    <CheckCircle2 size={16} style={{ verticalAlign: "middle", marginRight: "6px" }}/>
                    {repoSuccess}
                  </div>
                )}

                {repoReviewResult ? (
                  <div style={{ marginTop: "16px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px", padding: "12px 16px", background: "#111c2c", borderRadius: "8px", border: "1px solid #23344a" }}>
                      <div>
                        <b style={{ fontSize: "15px", color: "#e2ecf8" }}>{repoReviewResult.title}</b>
                        <div style={{ fontSize: "12px", color: "#8ba0bb", marginTop: "2px" }}>
                          Target: <code style={{ color: "#60a5fa" }}>{repoReviewResult.pull_request}</code> · Author: <b>{repoReviewResult.author}</b> · Lines: {repoReviewResult.analyzed_lines}
                        </div>
                      </div>
                      <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
                        <span style={{ fontSize: "14px", fontWeight: 700, padding: "6px 12px", borderRadius: "6px", background: repoReviewResult.score >= 80 ? "#11382d" : "#451c1c", color: repoReviewResult.score >= 80 ? "#74e2c0" : "#fca5a5", border: "1px solid currentColor" }}>
                          Score: {repoReviewResult.score}/100
                        </span>
                        <button className="text-btn" onClick={() => setActiveTab("PullRequests")}>
                          View in Pull Requests &rarr;
                        </button>
                      </div>
                    </div>

                    <div className="human-feedback-card" style={{ marginBottom: "16px" }}>
                      <div className="human-feedback-header">
                        <CheckCircle2 size={18} color="#40c6a5"/>
                        <span>Executive Review Synthesis</span>
                      </div>
                      <div style={{ whiteSpace: "pre-wrap", fontSize: "12.5px", color: "#cbd9ec", lineHeight: 1.6 }}>
                        {repoReviewResult.summary}
                      </div>
                    </div>

                    <div style={{ maxHeight: "450px", overflowY: "auto" }}>
                      {repoReviewResult.findings && repoReviewResult.findings.length > 0 ? (
                        repoReviewResult.findings.map((f, i) => (
                          <div className="result-finding" key={i} style={{ background: "#111c2c", padding: "14px", borderRadius: "8px", marginBottom: "10px", border: "1px solid #23344a" }}>
                            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                              <span className={"tag-pill " + f.severity}>{f.severity}</span>
                              <b style={{ fontSize: "13px", color: "#e2ecf8" }}>{f.title}</b>
                              {f.file_path && <span style={{ fontSize: "11px", color: "#7eaee9", fontFamily: "monospace" }}>{f.file_path}</span>}
                              {f.agent && <span style={{ fontSize: "10px", background: "#1a2c42", padding: "2px 6px", borderRadius: "4px", color: "#7eaee9", marginLeft: "auto" }}>{f.agent}</span>}
                            </div>
                            <small style={{ color: "#7e93af", display: "block", marginBottom: "6px" }}>
                              Line {f.line || "—"} · confidence {((f.confidence || 0.85) * 100).toFixed(0)}%
                            </small>
                            <p style={{ fontSize: "12px", color: "#a5b9d3", margin: "4px 0 8px" }}>{f.description}</p>
                            {f.suggestion && (
                              <div style={{ background: "#0a1320", border: "1px solid #1f2f45", borderRadius: "6px", padding: "8px 10px" }}>
                                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                                  <small style={{ color: "#60a5fa", fontWeight: 600 }}>Humanized Suggestion Fix:</small>
                                  <button
                                    onClick={() => copySuggestion(f.suggestion, `repo-${i}`)}
                                    style={{ background: "none", border: "none", color: "#7992b2", cursor: "pointer", display: "flex", alignItems: "center", gap: "4px", fontSize: "11px" }}
                                  >
                                    {copiedIdx === `repo-${i}` ? <><Check size={12} color="green"/> Copied</> : <><Copy size={12}/> Copy fix</>}
                                  </button>
                                </div>
                                <pre style={{ margin: 0, padding: "4px", fontSize: "11.5px", color: "#93c5fd" }}>
                                  <code>{f.suggestion}</code>
                                </pre>
                              </div>
                            )}
                          </div>
                        ))
                      ) : (
                        <div style={{ padding: "20px", textAlign: "center", color: "#74e2c0", background: "#0e241c", borderRadius: "8px" }}>
                          No high-priority security or correctness issues identified. Code looks clean!
                        </div>
                      )}
                    </div>
                  </div>
                ) : (
                  <div style={{ background: "#0a121e", border: "1px solid #1d2c3e", borderRadius: "8px", padding: "16px", color: "#7a90ac", fontSize: "12px", lineHeight: 1.6 }}>
                    <b>Supported GitHub URL Formats:</b>
                    <ul style={{ paddingLeft: "18px", margin: "8px 0 0" }}>
                      <li><b>Full Repository:</b> <code>https://github.com/Mahirlokare/ai-code-reviewer</code> or <code>owner/repo</code> (reviews latest PR or latest commits on default branch).</li>
                      <li><b>Pull Request:</b> <code>https://github.com/owner/repo/pull/123</code> (reviews pull request diff).</li>
                      <li><b>Specific Commit:</b> <code>https://github.com/owner/repo/commit/abc1234</code> (reviews commit diff).</li>
                      <li><b>Single File:</b> <code>https://github.com/owner/repo/blob/main/app/main.py</code> (runs full multi-agent audit on the file).</li>
                    </ul>
                  </div>
                )}
              </div>
            </div>
          )}


          {/* TAB 4: PULL REQUESTS FULL TABLE */}
          {activeTab === "PullRequests" && (
            <section className="panel pr-panel">
              <div className="panel-header">
                <div>
                  <h2>All Pull Requests</h2>
                  <p>Historical audit database with line-level findings and quality metrics</p>
                </div>
                <div className="table-tools">
                  <div className="searchbox">
                    <Search size={15}/>
                    <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search repositories or titles..."/>
                  </div>
                </div>
              </div>

              <div className="pr-table">
                <div className="pr-table-head">
                  <span>Pull request</span>
                  <span>Quality Score</span>
                  <span>Review Status</span>
                  <span>Updated</span>
                </div>
                {filteredPulls.map(pr => (
                  <div
                    className="pr-row"
                    key={pr.id}
                    style={{ cursor: "pointer" }}
                    onClick={() => setSelectedPr(pr)}
                  >
                    <div className="pr-title">
                      <div className="pr-icon"><GitPullRequest size={16}/></div>
                      <div>
                        <b>{pr.title}</b>
                        <small>{pr.repo} · {pr.id} · by @{pr.author}</small>
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
            </section>
          )}

          <footer>
            © 2026 ReviewPilot · AI Code Reviewer · Multi-Language & Multi-Platform Engine ·
            <a href="https://github.com/Mahirlokare/ai-code-reviewer" target="_blank" rel="noreferrer">
              GitHub Repository <ArrowUpRight size={13}/>
            </a>
          </footer>
        </div>
      </main>

      {/* Pull Request Audit Report Modal */}
      {selectedPr && (
        <div className="modal-backdrop" onClick={e => { if (e.target === e.currentTarget) setSelectedPr(null); }}>
          <div className="review-modal">
            <div className="modal-head">
              <div>
                <span className="eyebrow"><FileText size={13}/> PULL REQUEST AUDIT REPORT</span>
                <h2>{selectedPr.title} ({selectedPr.id})</h2>
                <small style={{ color: "#7e94af" }}>Repository: {selectedPr.repo} · Author: @{selectedPr.author}</small>
              </div>
              <button className="icon-btn" onClick={() => setSelectedPr(null)}><X/></button>
            </div>

            <div style={{ margin: "16px 0", padding: "14px", background: "#0c1523", border: "1px solid #1e2e42", borderRadius: "8px" }}>
              <b style={{ color: "#7eb9ff", fontSize: "13px" }}>Executive Summary:</b>
              <div style={{ whiteSpace: "pre-wrap", fontSize: "12.5px", color: "#cbd9ec", marginTop: "6px", lineHeight: 1.6 }}>
                {selectedPr.summary}
              </div>
            </div>

            <div className="result-head" style={{ marginBottom: "12px" }}>
              <b>Findings Breakdown ({selectedPr.findings ? selectedPr.findings.length : 0})</b>
              <span className="status-tag reviewed">Quality Score: {selectedPr.score}/100</span>
            </div>

            <div style={{ maxHeight: "400px", overflowY: "auto" }}>
              {selectedPr.findings && selectedPr.findings.length > 0 ? (
                selectedPr.findings.map((f, i) => (
                  <div className="result-finding" key={i} style={{ marginBottom: "12px", background: "#0e1827", padding: "12px", borderRadius: "8px", border: "1px solid #203147" }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap", marginBottom: "4px" }}>
                        <span className={"tag-pill " + f.severity}>{f.severity}</span>
                        <b style={{ fontSize: "12px" }}>{f.title}</b>
                        {f.agent && <span style={{ fontSize: "10px", background: "#1a2c42", padding: "2px 6px", borderRadius: "4px", color: "#7eaee9" }}>{f.agent}</span>}
                      </div>
                      <small style={{ color: "#7e93af", display: "block" }}>
                        {f.file_path || "File"} {f.line ? `· Line ${f.line}` : ""} · confidence {((f.confidence || 0.8) * 100).toFixed(0)}%
                      </small>
                      <p style={{ margin: "6px 0", color: "#a5b9d3", fontSize: "12px" }}>{f.description}</p>
                      {f.suggestion && (
                        <div style={{ marginTop: "6px", background: "#060c15", border: "1px solid #1a2738", borderRadius: "6px", padding: "8px" }}>
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                            <small style={{ fontWeight: 600, color: "#60a5fa" }}>One-Click Suggested Fix:</small>
                            <button
                              onClick={() => copySuggestion(f.suggestion, `modal-${i}`)}
                              style={{ background: "none", border: "none", cursor: "pointer", display: "flex", alignItems: "center", gap: "4px", fontSize: "11px", color: "#7c93b1" }}
                            >
                              {copiedIdx === `modal-${i}` ? <><Check size={12} color="green"/> Copied</> : <><Copy size={12}/> Copy fix</>}
                            </button>
                          </div>
                          <pre style={{ margin: 0, padding: "4px", fontSize: "12px", color: "#93c5fd" }}>
                            <code>{f.suggestion}</code>
                          </pre>
                        </div>
                      )}
                    </div>
                  </div>
                ))
              ) : (
                <p style={{ color: "#64748b", fontStyle: "italic" }}>No issues found in this pull request.</p>
              )}
            </div>
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
