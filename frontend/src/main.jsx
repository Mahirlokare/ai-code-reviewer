import React, { useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity, ArrowUpRight, Bell, Bot, CheckCircle2, ChevronDown, CircleHelp,
  Clock3, Code2, GitPullRequest, Github, LayoutDashboard, Menu, Search,
  Settings2, ShieldCheck, Sparkles, Terminal, TrendingUp, X, Zap
} from "lucide-react";
import "./styles.css";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";
const demoPulls = [
  { id: "#284", title: "Refactor authentication middleware", repo: "acme/platform-api", author: "sarahchen", time: "12 min ago", status: "Review needed", score: 82, files: 8, additions: 146, deletions: 39, avatar: "SC" },
  { id: "#283", title: "Add caching to user endpoints", repo: "acme/platform-api", author: "marcus-dev", time: "38 min ago", status: "Reviewed", score: 94, files: 4, additions: 89, deletions: 12, avatar: "MD" },
  { id: "#282", title: "Update payment retry logic", repo: "acme/checkout", author: "jlee", time: "1 hr ago", status: "Review needed", score: 67, files: 6, additions: 201, deletions: 54, avatar: "JL" },
  { id: "#281", title: "Fix pagination edge case", repo: "acme/platform-api", author: "alexr", time: "2 hrs ago", status: "Reviewed", score: 97, files: 2, additions: 31, deletions: 6, avatar: "AR" },
];
const demoFindings = [
  { severity: "high", title: "Potential hard-coded credential", file: "config/auth.py", line: "L42", detail: "A credential-like assignment was detected in the changed code.", fix: "Move secrets to environment-based configuration and rotate exposed credentials." },
  { severity: "medium", title: "Broad exception handling", file: "services/session.py", line: "L108", detail: "A broad exception handler may mask unrelated failures.", fix: "Catch expected exception types and log unexpected failures." },
  { severity: "low", title: "Debug print statement", file: "handlers/login.py", line: "L16", detail: "Debug output appears in the changed code.", fix: "Remove the print or use structured application logging." },
];
function App() {
  const [active, setActive] = useState("Overview");
  const [apiStatus, setApiStatus] = useState("Checking");
  const [reviewText, setReviewText] = useState("def login(user, password):\n    api_key = 'example-not-a-real-secret'\n    print('debug login')\n    try:\n        return authenticate(user, password)\n    except:\n        pass");
  const [reviewResult, setReviewResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [reviewError, setReviewError] = useState("");
  const [showReview, setShowReview] = useState(false);
  const [search, setSearch] = useState("");
  const [mobileMenu, setMobileMenu] = useState(false);
  const nav = [{ label: "Overview", icon: LayoutDashboard }, { label: "Pull Requests", icon: GitPullRequest }, { label: "Review Playground", icon: Code2 }, { label: "Analytics", icon: TrendingUp }];
  React.useEffect(() => { fetch(API_BASE + "/health").then(r => r.ok ? r.json() : Promise.reject()).then(() => setApiStatus("Online")).catch(() => setApiStatus("Offline")); }, []);
  const runReview = async () => {
    setBusy(true); setReviewError(""); setReviewResult(null);
    try {
      const diff = reviewText.split("\n").map(line => line.startsWith("+") || line.startsWith("-") || line.startsWith("@@") ? line : "+" + line).join("\n");
      const res = await fetch(API_BASE + "/api/v1/reviews", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ diff, language: "python" }) });
      if (!res.ok) throw new Error("Review API responded with " + res.status);
      setReviewResult(await res.json());
    } catch (e) { setReviewError(e.message + ". Ensure the backend is running at " + API_BASE); }
    finally { setBusy(false); }
  };
  const filtered = demoPulls.filter(p => (p.title + p.repo + p.author).toLowerCase().includes(search.toLowerCase()));
  const go = (label) => { setActive(label); setMobileMenu(false); if (label === "Review Playground") setShowReview(true); };
  return <div className="app-shell">
    <aside className={"sidebar " + (mobileMenu ? "mobile-open" : "")}>
      <div className="brand"><div className="brand-mark"><Bot size={21}/></div><div><strong>ReviewPilot</strong><small>AI code intelligence</small></div><button className="close-menu" onClick={() => setMobileMenu(false)}><X/></button></div>
      <div className="workspace"><div className="workspace-avatar">A</div><div><b>Acme Engineering</b><small>Workspace</small></div><ChevronDown size={15}/></div>
      <div className="nav-label">WORKSPACE</div>
      {nav.map(n => <button key={n.label} className={"nav-item " + (active === n.label ? "selected" : "")} onClick={() => go(n.label)}><n.icon size={18}/><span>{n.label}</span>{n.label === "Pull Requests" && <span className="nav-count">12</span>}</button>)}
      <div className="nav-label integrations-label">INTEGRATIONS</div>
      <button className="nav-item"><Github size={18}/><span>GitHub repositories</span><span className="connected-dot"/></button>
      <button className="nav-item"><ShieldCheck size={18}/><span>Security scans</span></button>
      <div className="sidebar-bottom"><div className="plan-card"><div className="plan-top"><Sparkles size={15}/> <b>ReviewPilot Pro</b></div><p>Unlock AI insights across every pull request.</p><button>Explore plan <ArrowUpRight size={14}/></button></div><button className="profile"><div className="profile-avatar">ML</div><div><b>Mahir Lokare</b><small>Developer</small></div><Settings2 size={17}/></button></div>
    </aside>
    {mobileMenu && <div className="overlay" onClick={() => setMobileMenu(false)}/>}
    <main className="main">
      <header className="topbar"><button className="hamburger" onClick={() => setMobileMenu(true)}><Menu/></button><div className="breadcrumbs">Workspace <span>/</span> <b>{active}</b></div><div className="top-actions"><div className="api-pill"><span className={"status-dot " + (apiStatus === "Online" ? "green" : apiStatus === "Offline" ? "red" : "")}/>{apiStatus === "Online" ? "API connected" : apiStatus === "Offline" ? "API offline" : "Checking API"}</div><button className="icon-btn" title="Help"><CircleHelp size={18}/></button><button className="icon-btn notification" title="Notifications"><Bell size={18}/><i/></button><div className="top-avatar">ML</div></div></header>
      <div className="content">
        <div className="welcome-row"><div><div className="eyebrow"><Sparkles size={14}/> INTELLIGENT CODE REVIEW</div><h1>Good morning, Mahir <span className="wave">✦</span></h1><p className="subtitle">Here's what's happening across your codebase today.</p></div><button className="primary-btn" onClick={() => {setActive("Review Playground");setShowReview(true)}}><Zap size={16}/> Run a code review</button></div>
        <div className="metrics-grid">
          <Metric icon={<GitPullRequest/>} label="Pull requests reviewed" value="128" change="+18.4%" caption="vs. last month" color="blue"/>
          <Metric icon={<ShieldCheck/>} label="Issues caught" value="346" change="+12.6%" caption="vs. last month" color="purple"/>
          <Metric icon={<Clock3/>} label="Review time saved" value="24.6 hrs" change="+8.2 hrs" caption="this month" color="mint"/>
          <Metric icon={<Activity/>} label="Review accuracy" value="94.8%" change="+2.1%" caption="vs. last month" color="orange"/>
        </div>
        <section className="panel activity-panel"><div className="panel-header"><div><h2>Review activity</h2><p>Automated review volume over the past 7 days</p></div><button className="select-btn">Last 7 days <ChevronDown size={15}/></button></div><div className="chart-wrap"><div className="chart-y"><span>60</span><span>40</span><span>20</span><span>0</span></div><div className="chart"><div className="grid-lines"><i/><i/><i/><i/></div><div className="bars">{[34,48,39,58,44,72,55,82,63,46,68,88,59,74,91,66,78,54,69,95,72,85,61,76,99,67,83,73].map((h,i)=><div className="bar-group" key={i}><div className="bar" style={{height: h+"%"}}/><div className="bar-secondary" style={{height: Math.max(10,h*.45)+"%"}}/></div>)}</div><div className="chart-x"><span>Mon</span><span>Tue</span><span>Wed</span><span>Thu</span><span>Fri</span><span>Sat</span><span>Sun</span></div></div></div><div className="chart-legend"><span><i className="legend-a"/>Reviews performed</span><span><i className="legend-b"/>Issues found</span></div></section>
        <section className="panel pr-panel"><div className="panel-header"><div><h2>Recent pull requests</h2><p>Latest activity from connected repositories</p></div><div className="table-tools"><div className="searchbox"><Search size={15}/><input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search pull requests"/></div><button className="select-btn">Filter <ChevronDown size={14}/></button></div></div><div className="pr-table"><div className="pr-table-head"><span>Pull request</span><span>AI score</span><span>Review status</span><span>Updated</span></div>{filtered.map(pr=><div className="pr-row" key={pr.id}><div className="pr-title"><div className="pr-icon"><GitPullRequest size={16}/></div><div><b>{pr.title}</b><small>{pr.repo} · {pr.id} · by {pr.author}</small></div></div><div className="score"><div className="score-ring" style={{"--score":pr.score}}><span>{pr.score}</span></div></div><div><span className={"status-tag " + (pr.status === "Reviewed" ? "reviewed" : "needed")}>{pr.status === "Reviewed" ? <CheckCircle2 size={13}/> : <Clock3 size={13}/>} {pr.status}</span></div><div className="updated">{pr.time}</div></div>)}</div><div className="panel-footer">Showing {filtered.length} of 12 pull requests <button onClick={()=>setActive("Pull Requests")}>View all pull requests <ArrowUpRight size={14}/></button></div></section>
        <div className="bottom-grid"><section className="panel findings-panel"><div className="panel-header"><div><h2>Top findings</h2><p>Most frequent issues from recent reviews</p></div><button className="text-btn">View report <ArrowUpRight size={14}/></button></div>{demoFindings.map((f,i)=><div className="finding-row" key={i}><span className={"severity " + f.severity}/><div><b>{f.title}</b><small>{f.file} : {f.line}</small></div><span className={"severity-label " + f.severity}>{f.severity}</span></div>)}</section><section className="panel engine-panel"><div className="panel-header"><div><h2>Review engine</h2><p>Live service status</p></div><span className="live-tag"><i/> LIVE</span></div><div className="engine-status"><div className="engine-icon"><Bot size={23}/></div><div><b>Heuristic engine</b><small>Baseline checks enabled</small></div><span className="online-tag">Active</span></div><div className="engine-status"><div className="engine-icon violet"><Sparkles size={23}/></div><div><b>AI review engine</b><small>Provider integration pending</small></div><span className="pending-tag">Coming soon</span></div><div className="engine-status"><div className="engine-icon green"><ShieldCheck size={23}/></div><div><b>Static analysis</b><small>Scanner integrations pending</small></div><span className="pending-tag">Coming soon</span></div><div className="engine-note"><Terminal size={14}/> Demo metrics are sample UI data. Reviews run against your backend.</div></section></div>
        <footer>© 2026 ReviewPilot <span>Built for better code, together.</span><a href="https://github.com/Mahirlokare/ai-code-reviewer" target="_blank" rel="noreferrer">GitHub repository <ArrowUpRight size={13}/></a></footer>
      </div>
    </main>
    {showReview && <div className="modal-backdrop" onClick={e=>{if(e.target===e.currentTarget)setShowReview(false)}}><div className="review-modal"><div className="modal-head"><div><span className="eyebrow"><Sparkles size={13}/> REVIEW PLAYGROUND</span><h2>Analyze code changes</h2></div><button className="icon-btn" onClick={()=>setShowReview(false)}><X/></button></div><p className="modal-desc">Paste a code diff or code snippet. The baseline backend currently runs transparent heuristic checks.</p><textarea className="code-input" value={reviewText} onChange={e=>setReviewText(e.target.value)} spellCheck="false"/><div className="modal-controls"><span className="api-hint"><span className={"status-dot "+(apiStatus==="Online"?"green":"red")}/>{apiStatus==="Online"?"Connected to local API":"API not connected"}</span><button className="primary-btn" disabled={busy||!reviewText.trim()} onClick={runReview}>{busy?<><Activity size={16}/> Reviewing…</>:<><Zap size={16}/> Analyze changes</>}</button></div>{reviewError&&<div className="error-box">{reviewError}</div>}{reviewResult&&<div className="review-output"><div className="result-head"><b>Review results</b><span>{reviewResult.findings.length} finding(s)</span></div><p>{reviewResult.summary}</p>{reviewResult.findings.map((f,i)=><div className="result-finding" key={i}><span className={"severity "+f.severity}/><div><b>{f.title}</b><small>{f.category} · {f.line? "Line "+f.line:"Line not identified"} · confidence {(f.confidence*100).toFixed(0)}%</small><p>{f.description}</p>{f.suggestion&&<em>Suggestion: {f.suggestion}</em>}</div></div>)}</div>}</div></div>}
  </div>;
}
function Metric({icon,label,value,change,caption,color}) {return <div className="metric-card"><div className={"metric-icon "+color}>{icon}</div><div className="metric-label">{label}</div><div className="metric-value">{value}</div><div className="metric-change"><span>{change}</span> <small>{caption}</small></div></div>}
createRoot(document.getElementById("root")).render(<App/>);