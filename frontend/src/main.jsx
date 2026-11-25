import React, { useState, useEffect } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity, ArrowUpRight, CheckCircle2, ChevronRight,
  Code2, GitPullRequest, Github, LayoutDashboard, Search,
  Shield, Terminal, X, RefreshCw, Copy, Check, FileText,
  Globe, Play, AlertTriangle, User, LogIn, LogOut, Mail,
  Lock, Settings, Key, ExternalLink, ShieldCheck
} from "lucide-react";
import "./styles.css";
import {
  getSupabase,
  isSupabaseConfigured,
  getSupabaseConfig,
  setCustomSupabaseConfig,
  supabaseSignUp,
  supabaseSignIn,
  supabaseSignOut,
  getSupabaseCurrentUser
} from "./supabase.js";

const formatApiBase = (raw) => {
  if (!raw) return "https://ai-code-reviewer-api-z7hr.onrender.com";
  let base = raw.trim();
  if (base.startsWith("/")) return base;
  if (!base.startsWith("http://") && !base.startsWith("https://")) {
    base = base.includes(".") ? `https://${base}` : `https://${base}.onrender.com`;
  }
  return base.replace(/\/+$/, "");
};

const API_BASE = formatApiBase(import.meta.env.VITE_API_BASE);

const safeFetchJson = async (url, options = {}) => {
  const res = await fetch(url, options);
  let text = "";
  try {
    text = await res.text();
  } catch (err) {
    throw new Error(`Failed to read response: ${err.message}`);
  }
  let data = null;
  if (text && text.trim()) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { detail: text.length > 300 ? text.slice(0, 300) + "..." : text };
    }
  }
  if (!res.ok) {
    const errorMsg = data?.detail || data?.message || `Request failed with HTTP status ${res.status}`;
    const error = new Error(errorMsg);
    error.status = res.status;
    error.data = data;
    throw error;
  }
  return data || {};
};

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
    label: "JavaScript",
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
    label: "Go",
    ext: "go",
    sample: `package main

import (
    "fmt"
    "os"
)

func ReadConfig(path string) error {
    file, err := os.Open(path)
    for i := 0; i < 5; i++ {
        defer file.Close() // Defer inside loop only runs when function returns
    }
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
        if (role == "ADMIN") { // String reference equality
            System.out.println("Admin access granted");
        }
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
  }
};

function App() {
  const [activeTab, setActiveTab] = useState("overview"); // overview | repo | code | prs
  const [apiStatus, setApiStatus] = useState("Checking...");
  const [pulls, setPulls] = useState([]);
  const [metrics, setMetrics] = useState({
    total_prs: 0,
    issues_caught: 0,
    critical_blocked: 0,
    accuracy: 95
  });

  // User Auth State
  const [user, setUser] = useState(null);
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [authMode, setAuthMode] = useState("signin"); // signin | signup | config
  const [authEmail, setAuthEmail] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [authFullName, setAuthFullName] = useState("");
  const [authBusy, setAuthBusy] = useState(false);
  const [authError, setAuthError] = useState("");
  const [authSuccess, setAuthSuccess] = useState("");
  const [userMenuOpen, setUserMenuOpen] = useState(false);

  // Supabase Config State
  const [sbUrl, setSbUrl] = useState(getSupabaseConfig().url);
  const [sbKey, setSbKey] = useState(getSupabaseConfig().anonKey);
  const [useSupabase, setUseSupabase] = useState(isSupabaseConfigured());

  // Email Confirmation Modal State
  const [emailModalOpen, setEmailModalOpen] = useState(false);
  const [sentEmails, setSentEmails] = useState([]);
  const [emailLoading, setEmailLoading] = useState(false);

  // Direct Code Runner State
  const [selectedLang, setSelectedLang] = useState("python");
  const [codeSnippet, setCodeSnippet] = useState(MULTI_LANG_PRESETS["python"].sample);
  const [codeBusy, setCodeBusy] = useState(false);
  const [codeError, setCodeError] = useState("");
  const [codeResult, setCodeResult] = useState(null);

  // Remote Repository State
  const [repoInput, setRepoInput] = useState("https://github.com/Mahirlokare/ai-code-reviewer");
  const [repoBusy, setRepoBusy] = useState(false);
  const [repoError, setRepoError] = useState("");
  const [repoSuccess, setRepoSuccess] = useState("");
  const [repoResult, setRepoResult] = useState(null);

  // PR Inspection Modal
  const [selectedPr, setSelectedPr] = useState(null);
  const [copiedIndex, setCopiedIndex] = useState(null);

  // Check auth and health on load
  useEffect(() => {
    // 1. Check Supabase session
    getSupabaseCurrentUser().then((sbUser) => {
      if (sbUser) {
        setUser(sbUser);
        // Sync to backend
        fetch(API_BASE + "/api/v1/auth/supabase-sync", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            user_id: sbUser.id,
            email: sbUser.email,
            username: sbUser.username,
            full_name: sbUser.full_name,
          }),
        }).catch(() => {});
      } else {
        // Fallback to local stored user
        const stored = localStorage.getItem("reviewpilot_user");
        if (stored) {
          try { setUser(JSON.parse(stored)); } catch {}
        }
      }
    });

    // 2. Fetch live health and metrics
    fetchLiveState();
    const timer = setInterval(fetchLiveState, 20000);
    return () => clearInterval(timer);
  }, []);

  const fetchLiveState = () => {
    safeFetchJson(API_BASE + "/health")
      .then(() => {
        setApiStatus("Online");
        safeFetchJson(API_BASE + "/api/v1/pull-requests")
          .then(data => { if (Array.isArray(data)) setPulls(data); })
          .catch(() => {});

        safeFetchJson(API_BASE + "/api/v1/metrics")
          .then(m => {
            setMetrics({
              total_prs: m.total_pull_requests || 0,
              issues_caught: m.total_findings || 0,
              critical_blocked: m.critical_issues_blocked || 0,
              accuracy: m.average_quality_score || 95,
            });
          })
          .catch(() => {});
      })
      .catch(() => setApiStatus("Offline"));
  };

  const handleAuth = async (e) => {
    e.preventDefault();
    setAuthBusy(true);
    setAuthError("");
    setAuthSuccess("");

    try {
      if (authMode === "config") {
        setCustomSupabaseConfig(sbUrl, sbKey);
        setUseSupabase(Boolean(sbUrl && sbKey));
        setAuthSuccess("Supabase configuration updated successfully.");
        setTimeout(() => setAuthModalOpen(false), 1000);
        return;
      }

      // If Supabase is configured, use Supabase Auth
      if (isSupabaseConfigured()) {
        if (authMode === "signup") {
          const res = await supabaseSignUp(authEmail, authPassword, {
            fullName: authFullName,
            username: authEmail.split("@")[0]
          });
          setAuthSuccess("Registration initiated! Supabase has dispatched a confirmation email to " + authEmail + ". Check your inbox to verify your account.");
          if (res.user) {
            const u = {
              id: res.user.id,
              email: res.user.email,
              username: authEmail.split("@")[0],
              full_name: authFullName,
              provider: "supabase",
            };
            setUser(u);
            localStorage.setItem("reviewpilot_user", JSON.stringify(u));
          }
        } else {
          const res = await supabaseSignIn(authEmail, authPassword);
          if (res.user) {
            const u = {
              id: res.user.id,
              email: res.user.email,
              username: res.user.user_metadata?.username || authEmail.split("@")[0],
              full_name: res.user.user_metadata?.full_name || "",
              provider: "supabase",
              token: res.session?.access_token,
            };
            setUser(u);
            localStorage.setItem("reviewpilot_user", JSON.stringify(u));
            setAuthSuccess("Signed in successfully via Supabase Auth.");
            setTimeout(() => setAuthModalOpen(false), 1000);
          }
        }
      } else {
        // Fallback to backend local auth engine
        const endpoint = authMode === "signup" ? "/api/v1/auth/signup" : "/api/v1/auth/signin";
        const payload = authMode === "signup"
          ? { username: authEmail.split("@")[0], email: authEmail, password: authPassword, full_name: authFullName }
          : { username_or_email: authEmail, password: authPassword };

        const data = await safeFetchJson(API_BASE + endpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });

        setUser(data.user);
        localStorage.setItem("reviewpilot_user", JSON.stringify(data.user));
        localStorage.setItem("reviewpilot_token", data.token);
        setAuthSuccess(data.message || "Authenticated successfully.");
        setTimeout(() => setAuthModalOpen(false), 1200);
      }
    } catch (err) {
      setAuthError(err.message || "Authentication error occurred.");
    } finally {
      setAuthBusy(false);
    }
  };

  const handleSignOut = async () => {
    await supabaseSignOut();
    setUser(null);
    localStorage.removeItem("reviewpilot_user");
    localStorage.removeItem("reviewpilot_token");
    setUserMenuOpen(false);
  };

  const loadEmails = async () => {
    setEmailLoading(true);
    setEmailModalOpen(true);
    try {
      const q = user?.email ? `?recipient=${encodeURIComponent(user.email)}` : "";
      const data = await safeFetchJson(API_BASE + "/api/v1/auth/emails" + q);
      if (Array.isArray(data)) {
        setSentEmails(data);
      }
    } catch (e) {
      console.warn("Could not load email list:", e);
    } finally {
      setEmailLoading(false);
    }
  };

  const runCodeReview = async () => {
    setCodeBusy(true);
    setCodeError("");
    setCodeResult(null);
    try {
      const data = await safeFetchJson(API_BASE + "/api/v1/code/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          code: codeSnippet,
          language: selectedLang,
          filename: `snippet.${MULTI_LANG_PRESETS[selectedLang].ext}`
        })
      });
      setCodeResult(data);
    } catch (e) {
      setCodeError(e.message || "Failed to analyze code snippet.");
    } finally {
      setCodeBusy(false);
    }
  };

  const runRepoReview = async () => {
    if (!repoInput.trim()) return;
    setRepoBusy(true);
    setRepoError("");
    setRepoSuccess("");
    setRepoResult(null);
    try {
      const data = await safeFetchJson(API_BASE + "/api/v1/repos/fetch-and-review", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo_url_or_slug: repoInput.trim() })
      });
      setRepoResult(data);
      setRepoSuccess(`Audit complete for ${data.pull_request}! Quality score: ${data.score}/100.`);
      fetchLiveState();
    } catch (e) {
      setRepoError(e.message || "Failed to audit repository target.");
    } finally {
      setRepoBusy(false);
    }
  };

  const copyPatch = (patchText, idx) => {
    navigator.clipboard.writeText(patchText);
    setCopiedIndex(idx);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  return (
    <div className="app-shell">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-title">
            <Shield size={18} style={{ color: "var(--accent)" }}/>
            <span>ReviewPilot</span>
          </div>
          <span className="brand-badge">v0.2</span>
        </div>

        <nav className="nav-section">
          <div className="nav-label">Navigation</div>
          <button
            className={"nav-item " + (activeTab === "overview" ? "active" : "")}
            onClick={() => setActiveTab("overview")}
          >
            <LayoutDashboard size={16}/>
            <span>Overview</span>
          </button>
          <button
            className={"nav-item " + (activeTab === "repo" ? "active" : "")}
            onClick={() => setActiveTab("repo")}
          >
            <Globe size={16}/>
            <span>Review Repository</span>
          </button>
          <button
            className={"nav-item " + (activeTab === "code" ? "active" : "")}
            onClick={() => setActiveTab("code")}
          >
            <Code2 size={16}/>
            <span>Code Runner</span>
          </button>
          <button
            className={"nav-item " + (activeTab === "prs" ? "active" : "")}
            onClick={() => setActiveTab("prs")}
          >
            <GitPullRequest size={16}/>
            <span>Pull Requests</span>
          </button>

          <div className="nav-label" style={{ marginTop: "16px" }}>Engine Health</div>
          <div style={{ padding: "8px 10px", fontSize: "11px", color: "var(--text-secondary)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "4px" }}>
              <span className={"status-dot " + (apiStatus === "Online" ? "online" : "offline")}/>
              <span>Core Review Engine</span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <span className={"status-dot " + (isSupabaseConfigured() ? "online" : "online")}/>
              <span>{isSupabaseConfigured() ? "Supabase Auth" : "Built-in Auth"}</span>
            </div>
          </div>
        </nav>

        <div className="sidebar-footer">
          {user ? (
            <div className="user-card" onClick={() => setUserMenuOpen(!userMenuOpen)}>
              <div className={"user-avatar " + (user.provider === "supabase" ? "supabase" : "")}>
                {user.username.slice(0, 2).toUpperCase()}
              </div>
              <div className="user-info">
                <div className="user-name">@{user.username}</div>
                <div className="user-email">{user.email}</div>
              </div>
            </div>
          ) : (
            <div style={{ display: "flex", gap: "6px" }}>
              <button
                className="btn btn-secondary"
                style={{ flex: 1, fontSize: "11.5px" }}
                onClick={() => { setAuthMode("signin"); setAuthError(""); setAuthSuccess(""); setAuthModalOpen(true); }}
              >
                <LogIn size={13}/> Sign in
              </button>
              <button
                className="btn btn-primary"
                style={{ flex: 1, fontSize: "11.5px" }}
                onClick={() => { setAuthMode("signup"); setAuthError(""); setAuthSuccess(""); setAuthModalOpen(true); }}
              >
                Sign up
              </button>
            </div>
          )}
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="main-wrapper">
        <header className="top-header">
          <div className="header-left">
            <span className="header-title">
              {activeTab === "overview" && "System Dashboard"}
              {activeTab === "repo" && "Universal GitHub Repository Audit"}
              {activeTab === "code" && "Multi-Language Direct Code Runner"}
              {activeTab === "prs" && "Processed Pull Requests"}
            </span>
          </div>

          <div className="header-right">
            <div
              className="status-indicator"
              onClick={fetchLiveState}
              title="Click to refresh server connection"
            >
              <span className={"status-dot " + (apiStatus === "Online" ? "online" : "offline")}/>
              <span>{apiStatus === "Online" ? "API Connected" : "Connecting..."}</span>
            </div>

            <button
              className="btn btn-outline"
              style={{ padding: "4px 8px" }}
              title="Supabase Settings"
              onClick={() => { setAuthMode("config"); setAuthError(""); setAuthSuccess(""); setAuthModalOpen(true); }}
            >
              <Settings size={14}/>
            </button>

            {user ? (
              <div style={{ position: "relative" }}>
                <button
                  className="btn btn-secondary"
                  onClick={() => setUserMenuOpen(!userMenuOpen)}
                >
                  <User size={13}/>
                  <span>@{user.username}</span>
                </button>
                {userMenuOpen && (
                  <div className="dropdown-menu">
                    <div style={{ padding: "8px 10px", borderBottom: "1px solid var(--border-color)", marginBottom: "4px" }}>
                      <div style={{ fontWeight: 600, fontSize: "12px", color: "var(--text-primary)" }}>{user.full_name || user.username}</div>
                      <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>{user.email}</div>
                      <div style={{ fontSize: "10px", color: "#34d399", marginTop: "3px" }}>
                        ✓ {user.provider === "supabase" ? "Supabase Authenticated" : "Verified Account"}
                      </div>
                    </div>
                    <button className="dropdown-item" onClick={() => { setUserMenuOpen(false); loadEmails(); }}>
                      <Mail size={13}/>
                      <span>Confirmation Emails</span>
                    </button>
                    <button className="dropdown-item danger" onClick={handleSignOut}>
                      <LogOut size={13}/>
                      <span>Sign out</span>
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <button
                className="btn btn-secondary"
                onClick={() => { setAuthMode("signin"); setAuthError(""); setAuthSuccess(""); setAuthModalOpen(true); }}
              >
                <LogIn size={13}/> Sign in
              </button>
            )}
          </div>
        </header>

        <main className="page-content">
          {/* TAB 1: OVERVIEW */}
          {activeTab === "overview" && (
            <div>
              <div className="page-header">
                <h1 className="page-title">Code Review Dashboard</h1>
                <p className="page-description">
                  Automated security analysis, bug detection, and style review for pull requests and repositories.
                </p>
              </div>

              <div className="stat-grid">
                <div className="stat-box">
                  <div className="stat-label">Pull Requests Audited</div>
                  <div className="stat-value">{metrics.total_prs}</div>
                  <div className="stat-caption">Processed reviews</div>
                </div>
                <div className="stat-box">
                  <div className="stat-label">Total Findings</div>
                  <div className="stat-value">{metrics.issues_caught}</div>
                  <div className="stat-caption">Issues flagged</div>
                </div>
                <div className="stat-box">
                  <div className="stat-label">Critical Issues Blocked</div>
                  <div className="stat-value">{metrics.critical_blocked}</div>
                  <div className="stat-caption">High & Critical</div>
                </div>
                <div className="stat-box">
                  <div className="stat-label">Average Quality Score</div>
                  <div className="stat-value">{metrics.accuracy}%</div>
                  <div className="stat-caption">Passing benchmark</div>
                </div>
              </div>

              <div className="card">
                <div className="card-header">
                  <div>
                    <div className="card-title">Quick Actions</div>
                    <div className="card-desc">Audit any repository or test snippets directly</div>
                  </div>
                </div>
                <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
                  <button className="btn btn-primary" onClick={() => setActiveTab("repo")}>
                    <Globe size={14}/> Audit a GitHub Repository
                  </button>
                  <button className="btn btn-secondary" onClick={() => setActiveTab("code")}>
                    <Code2 size={14}/> Open Direct Code Runner
                  </button>
                  <button className="btn btn-outline" onClick={() => window.open("https://github.com/Mahirlokare/ai-code-reviewer", "_blank")}>
                    <Github size={14}/> View Repository on GitHub
                  </button>
                </div>
              </div>

              <div className="card">
                <div className="card-header">
                  <div className="card-title">Recent Pull Requests</div>
                  <button className="btn btn-outline" onClick={() => setActiveTab("prs")}>
                    View All →
                  </button>
                </div>
                <div className="table-container">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Pull Request</th>
                        <th>Repository</th>
                        <th>Author</th>
                        <th>Findings</th>
                        <th>Score</th>
                      </tr>
                    </thead>
                    <tbody>
                      {pulls.slice(0, 5).map((p, idx) => (
                        <tr key={idx} style={{ cursor: "pointer" }} onClick={() => setSelectedPr(p)}>
                          <td style={{ fontWeight: 600 }}>#{p.number} {p.title}</td>
                          <td style={{ color: "var(--text-secondary)" }}>{p.repo}</td>
                          <td style={{ color: "var(--text-muted)" }}>@{p.author}</td>
                          <td>
                            <span className="badge badge-low">{p.findings?.length || 0} items</span>
                          </td>
                          <td>
                            <span style={{ fontWeight: 700, color: p.score >= 80 ? "#34d399" : p.score >= 60 ? "#fbbf24" : "#f87171" }}>
                              {p.score}/100
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: REVIEW ANY REPOSITORY */}
          {activeTab === "repo" && (
            <div>
              <div className="page-header">
                <h1 className="page-title">Review Repository</h1>
                <p className="page-description">
                  Enter any public GitHub repository, PR, commit, or file URL. The multi-agent pipeline extracts diffs and runs security analysis.
                </p>
              </div>

              <div className="card">
                <div className="input-row" style={{ marginBottom: "12px" }}>
                  <input
                    type="text"
                    className="input-field"
                    placeholder="e.g. https://github.com/owner/repo, owner/repo#12, or commit URL"
                    value={repoInput}
                    onChange={e => setRepoInput(e.target.value)}
                  />
                  <button
                    className="btn btn-primary"
                    disabled={repoBusy || !repoInput.trim()}
                    onClick={runRepoReview}
                  >
                    {repoBusy ? "Auditing..." : "Audit Repository"}
                  </button>
                </div>
                <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                  Supports full repositories (auto-analyzes latest commit patch), specific PRs (`/pull/1`), commits (`/commit/sha`), or slugs (`owner/repo`).
                </div>

                {repoError && (
                  <div className="alert alert-error" style={{ marginTop: "14px" }}>
                    <AlertTriangle size={15}/>
                    <span>{repoError}</span>
                  </div>
                )}

                {repoSuccess && (
                  <div className="alert alert-success" style={{ marginTop: "14px" }}>
                    <CheckCircle2 size={15}/>
                    <span>{repoSuccess}</span>
                  </div>
                )}
              </div>

              {repoResult && (
                <div className="card">
                  <div className="card-header">
                    <div>
                      <div className="card-title">{repoResult.title || repoResult.pull_request}</div>
                      <div className="card-desc">Target: {repoResult.pull_request} · Analyzed {repoResult.analyzed_lines} lines</div>
                    </div>
                    <span style={{ fontSize: "18px", fontWeight: 700, color: repoResult.score >= 80 ? "#34d399" : "#fbbf24" }}>
                      Score: {repoResult.score}/100
                    </span>
                  </div>

                  <p style={{ fontSize: "13px", color: "var(--text-secondary)", marginBottom: "16px" }}>
                    {repoResult.summary}
                  </p>

                  <div className="findings-container">
                    {repoResult.findings?.map((f, i) => (
                      <div key={i} className={"finding-item " + (f.severity || "medium")}>
                        <div className="finding-header">
                          <span className="finding-title">{f.title}</span>
                          <span className={"badge badge-" + (f.severity || "medium")}>{f.severity}</span>
                        </div>
                        <div className="finding-meta">
                          {f.file_path || "file"} : Line {f.line || "—"} · Agent: {f.agent || "Security"}
                        </div>
                        <div className="finding-desc">{f.description}</div>
                        {f.suggestion && (
                          <div style={{ marginTop: "8px" }}>
                            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", color: "var(--text-muted)", marginBottom: "4px" }}>
                              <span>Suggested Remediation</span>
                              <button
                                className="btn btn-outline"
                                style={{ height: "22px", padding: "2px 8px", fontSize: "10px" }}
                                onClick={() => copyPatch(f.suggestion, i)}
                              >
                                {copiedIndex === i ? <Check size={11}/> : <Copy size={11}/>}
                                {copiedIndex === i ? "Copied" : "Copy"}
                              </button>
                            </div>
                            <pre className="patch-block">{f.suggestion}</pre>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 3: DIRECT CODE RUNNER */}
          {activeTab === "code" && (
            <div>
              <div className="page-header">
                <h1 className="page-title">Direct Code Runner</h1>
                <p className="page-description">
                  Paste or edit source code in any language to run multi-agent security and syntax checks in real time.
                </p>
              </div>

              <div className="card">
                <div className="lang-bar">
                  {Object.entries(MULTI_LANG_PRESETS).map(([k, p]) => (
                    <button
                      key={k}
                      className={"lang-btn " + (selectedLang === k ? "active" : "")}
                      onClick={() => {
                        setSelectedLang(k);
                        setCodeSnippet(p.sample);
                        setCodeResult(null);
                        setCodeError("");
                      }}
                    >
                      {p.label}
                    </button>
                  ))}
                </div>

                <textarea
                  className="code-textarea"
                  value={codeSnippet}
                  onChange={e => setCodeSnippet(e.target.value)}
                  placeholder="Paste your source code here..."
                />

                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "12px" }}>
                  <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                    Multi-agent review: OWASP security rules, memory safety, syntax, and performance.
                  </span>
                  <button
                    className="btn btn-primary"
                    disabled={codeBusy || !codeSnippet.trim()}
                    onClick={runCodeReview}
                  >
                    <Play size={13}/>
                    {codeBusy ? "Running Analysis..." : "Run Analysis"}
                  </button>
                </div>

                {codeError && (
                  <div className="alert alert-error" style={{ marginTop: "14px" }}>
                    <AlertTriangle size={15}/>
                    <span>{codeError}</span>
                  </div>
                )}
              </div>

              {codeResult && (
                <div className="card">
                  <div className="card-header">
                    <div>
                      <div className="card-title">Analysis Results</div>
                      <div className="card-desc">{codeResult.findings?.length || 0} issue(s) identified in {selectedLang}</div>
                    </div>
                  </div>

                  <p style={{ fontSize: "13px", color: "var(--text-secondary)", marginBottom: "16px" }}>
                    {codeResult.summary}
                  </p>

                  <div className="findings-container">
                    {codeResult.findings?.map((f, i) => (
                      <div key={i} className={"finding-item " + (f.severity || "medium")}>
                        <div className="finding-header">
                          <span className="finding-title">{f.title}</span>
                          <span className={"badge badge-" + (f.severity || "medium")}>{f.severity}</span>
                        </div>
                        <div className="finding-meta">Line {f.line || "—"} · Agent: {f.agent}</div>
                        <div className="finding-desc">{f.description}</div>
                        {f.suggestion && (
                          <div style={{ marginTop: "8px" }}>
                            <pre className="patch-block">{f.suggestion}</pre>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 4: PULL REQUESTS */}
          {activeTab === "prs" && (
            <div>
              <div className="page-header">
                <h1 className="page-title">Pull Requests History</h1>
                <p className="page-description">
                  Audited pull request records stored persistently. Click on any row to inspect modified context and actionable recommendations.
                </p>
              </div>

              <div className="table-container">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Pull Request</th>
                      <th>Repository</th>
                      <th>Author</th>
                      <th>Findings</th>
                      <th>Quality Score</th>
                      <th>Date</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pulls.map((p, idx) => (
                      <tr key={idx} style={{ cursor: "pointer" }} onClick={() => setSelectedPr(p)}>
                        <td style={{ fontWeight: 600 }}>#{p.number} {p.title}</td>
                        <td style={{ color: "var(--text-secondary)" }}>{p.repo}</td>
                        <td style={{ color: "var(--text-muted)" }}>@{p.author}</td>
                        <td>
                          <span className="badge badge-low">{p.findings?.length || 0} findings</span>
                        </td>
                        <td>
                          <span style={{ fontWeight: 700, color: p.score >= 80 ? "#34d399" : p.score >= 60 ? "#fbbf24" : "#f87171" }}>
                            {p.score}/100
                          </span>
                        </td>
                        <td style={{ color: "var(--text-muted)", fontSize: "11px" }}>
                          {new Date(p.created_at * 1000).toLocaleDateString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </main>
      </div>

      {/* PR Diff Modal */}
      {selectedPr && (
        <div className="modal-overlay" onClick={e => { if (e.target === e.currentTarget) setSelectedPr(null); }}>
          <div className="modal-card" style={{ maxWidth: "720px" }}>
            <div className="modal-header">
              <div>
                <div className="modal-title">Pull Request #{selectedPr.number}: {selectedPr.title}</div>
                <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "2px" }}>
                  Repository: {selectedPr.repo} · Author: @{selectedPr.author} · Quality: {selectedPr.score}/100
                </div>
              </div>
              <button className="close-btn" onClick={() => setSelectedPr(null)}><X size={16}/></button>
            </div>

            <p style={{ fontSize: "13px", color: "var(--text-secondary)", marginBottom: "16px" }}>
              {selectedPr.summary}
            </p>

            <div className="findings-container">
              {selectedPr.findings?.map((f, i) => (
                <div key={i} className={"finding-item " + (f.severity || "medium")}>
                  <div className="finding-header">
                    <span className="finding-title">{f.title}</span>
                    <span className={"badge badge-" + (f.severity || "medium")}>{f.severity}</span>
                  </div>
                  <div className="finding-meta">
                    {f.file_path || "source.py"} : Line {f.line || "—"} · Agent: {f.agent}
                  </div>
                  <div className="finding-desc">{f.description}</div>
                  {f.suggestion && <pre className="patch-block">{f.suggestion}</pre>}
                </div>
              ))}
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "20px" }}>
              <button className="btn btn-secondary" onClick={() => setSelectedPr(null)}>Close</button>
            </div>
          </div>
        </div>
      )}

      {/* Authentication & Supabase Configuration Modal */}
      {authModalOpen && (
        <div className="modal-overlay" onClick={e => { if (e.target === e.currentTarget) setAuthModalOpen(false); }}>
          <div className="modal-card" style={{ maxWidth: "440px" }}>
            <div className="modal-header">
              <div>
                <div className="modal-title">
                  {authMode === "signup" && "Create Account"}
                  {authMode === "signin" && "Sign In"}
                  {authMode === "config" && "Supabase Settings"}
                </div>
                <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "2px" }}>
                  {authMode === "config"
                    ? "Connect your Supabase project for managed authentication and confirmation emails."
                    : isSupabaseConfigured()
                    ? "Secured by Supabase Auth (confirmation email automatically sent)"
                    : "ReviewPilot Developer Access"}
                </div>
              </div>
              <button className="close-btn" onClick={() => setAuthModalOpen(false)}><X size={16}/></button>
            </div>

            {authMode !== "config" && (
              <div style={{ display: "flex", gap: "6px", marginBottom: "16px", background: "var(--bg-elevated)", padding: "3px", borderRadius: "6px" }}>
                <button
                  type="button"
                  className={"btn " + (authMode === "signin" ? "btn-secondary" : "btn-outline")}
                  style={{ flex: 1, border: "none" }}
                  onClick={() => { setAuthMode("signin"); setAuthError(""); setAuthSuccess(""); }}
                >
                  Sign In
                </button>
                <button
                  type="button"
                  className={"btn " + (authMode === "signup" ? "btn-secondary" : "btn-outline")}
                  style={{ flex: 1, border: "none" }}
                  onClick={() => { setAuthMode("signup"); setAuthError(""); setAuthSuccess(""); }}
                >
                  Sign Up
                </button>
              </div>
            )}

            <form onSubmit={handleAuth}>
              {authMode === "config" ? (
                <>
                  <div style={{ marginBottom: "12px" }}>
                    <label style={{ display: "block", fontSize: "11px", fontWeight: 600, color: "var(--text-muted)", marginBottom: "4px" }}>
                      SUPABASE PROJECT URL
                    </label>
                    <input
                      type="url"
                      className="input-field"
                      placeholder="https://your-project.supabase.co"
                      value={sbUrl}
                      onChange={e => setSbUrl(e.target.value)}
                    />
                  </div>
                  <div style={{ marginBottom: "16px" }}>
                    <label style={{ display: "block", fontSize: "11px", fontWeight: 600, color: "var(--text-muted)", marginBottom: "4px" }}>
                      SUPABASE ANON KEY
                    </label>
                    <input
                      type="password"
                      className="input-field"
                      placeholder="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
                      value={sbKey}
                      onChange={e => setSbKey(e.target.value)}
                    />
                  </div>
                  <button type="submit" className="btn btn-supabase" style={{ width: "100%" }}>
                    Save Supabase Configuration
                  </button>
                </>
              ) : (
                <>
                  {authMode === "signup" && (
                    <div style={{ marginBottom: "12px" }}>
                      <label style={{ display: "block", fontSize: "11px", fontWeight: 600, color: "var(--text-muted)", marginBottom: "4px" }}>
                        FULL NAME (OPTIONAL)
                      </label>
                      <input
                        type="text"
                        className="input-field"
                        placeholder="Sarah Connor"
                        value={authFullName}
                        onChange={e => setAuthFullName(e.target.value)}
                      />
                    </div>
                  )}

                  <div style={{ marginBottom: "12px" }}>
                    <label style={{ display: "block", fontSize: "11px", fontWeight: 600, color: "var(--text-muted)", marginBottom: "4px" }}>
                      EMAIL ADDRESS
                    </label>
                    <input
                      type="email"
                      required
                      className="input-field"
                      placeholder="developer@company.com"
                      value={authEmail}
                      onChange={e => setAuthEmail(e.target.value)}
                    />
                  </div>

                  <div style={{ marginBottom: "16px" }}>
                    <label style={{ display: "block", fontSize: "11px", fontWeight: 600, color: "var(--text-muted)", marginBottom: "4px" }}>
                      PASSWORD
                    </label>
                    <input
                      type="password"
                      required
                      className="input-field"
                      placeholder="Minimum 6 characters"
                      value={authPassword}
                      onChange={e => setAuthPassword(e.target.value)}
                    />
                  </div>

                  {authMode === "signup" && (
                    <div style={{ fontSize: "11.5px", color: "var(--text-muted)", marginBottom: "14px", display: "flex", alignItems: "center", gap: "6px" }}>
                      <Mail size={13} style={{ color: "var(--supabase-green)" }}/>
                      <span>A confirmation email will be sent directly to your address.</span>
                    </div>
                  )}

                  {authError && (
                    <div className="alert alert-error">
                      <span>{authError}</span>
                    </div>
                  )}

                  {authSuccess && (
                    <div className="alert alert-success">
                      <CheckCircle2 size={14}/>
                      <span>{authSuccess}</span>
                    </div>
                  )}

                  <button
                    type="submit"
                    className={"btn " + (isSupabaseConfigured() ? "btn-supabase" : "btn-primary")}
                    style={{ width: "100%" }}
                    disabled={authBusy}
                  >
                    {authBusy ? "Processing..." : authMode === "signup" ? "Create Account & Send Confirmation Email" : "Sign In"}
                  </button>

                  <div style={{ marginTop: "14px", textAlign: "center" }}>
                    <button
                      type="button"
                      style={{ background: "none", border: "none", color: "var(--text-muted)", fontSize: "11px", cursor: "pointer", textDecoration: "underline" }}
                      onClick={() => setAuthMode("config")}
                    >
                      {isSupabaseConfigured() ? "⚙️ Supabase Configured (Click to change)" : "⚙️ Configure custom Supabase project"}
                    </button>
                  </div>
                </>
              )}
            </form>
          </div>
        </div>
      )}

      {/* Confirmation Email Viewer Modal */}
      {emailModalOpen && (
        <div className="modal-overlay" onClick={e => { if (e.target === e.currentTarget) setEmailModalOpen(false); }}>
          <div className="modal-card" style={{ maxWidth: "680px" }}>
            <div className="modal-header">
              <div>
                <div className="modal-title">Email Notification Log</div>
                <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "2px" }}>
                  Verified delivery records for confirmation emails and sign-in notices.
                </div>
              </div>
              <button className="close-btn" onClick={() => setEmailModalOpen(false)}><X size={16}/></button>
            </div>

            {emailLoading ? (
              <div style={{ padding: "20px", textAlign: "center", color: "var(--text-muted)" }}>Loading email records...</div>
            ) : sentEmails.length === 0 ? (
              <div style={{ padding: "20px", textAlign: "center", color: "var(--text-muted)" }}>
                No confirmation emails found. Register an account to trigger one.
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                {sentEmails.map(eml => (
                  <div key={eml.id} className="card" style={{ padding: "14px", margin: 0 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                      <span style={{ fontWeight: 600, fontSize: "13px" }}>{eml.subject}</span>
                      <span className="badge badge-low" style={{ color: "#34d399", background: "rgba(52, 211, 153, 0.1)" }}>
                        ✓ {eml.status}
                      </span>
                    </div>
                    <div style={{ fontSize: "11px", color: "var(--text-muted)", marginBottom: "8px" }}>
                      To: {eml.recipient} · {new Date(eml.created_at * 1000).toLocaleString()}
                    </div>
                    <div
                      style={{ background: "var(--bg-page)", padding: "12px", borderRadius: "6px", border: "1px solid var(--border-color)", fontSize: "12px" }}
                      dangerouslySetInnerHTML={{ __html: eml.body_html }}
                    />
                  </div>
                ))}
              </div>
            )}

            <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "16px" }}>
              <button className="btn btn-secondary" onClick={() => setEmailModalOpen(false)}>Close</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App />);
