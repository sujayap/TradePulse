
import { useEffect, useState } from "react";
import {
  Activity,
  FileText,
  GitBranch,
  RefreshCw,
  ShieldCheck,
  ExternalLink,
  Clock3,
  LayoutDashboard,
} from "lucide-react";
import "./App.css";

const API = "http://127.0.0.1:8000";

function App() {
  const [dashboard, setDashboard] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [changes, setChanges] = useState([]);
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadData() {
    try {
      setError("");

      const responses = await Promise.all([
        fetch(`${API}/api/dashboard`),
        fetch(`${API}/api/documents?limit=50`),
        fetch(`${API}/api/changes?limit=20`),
        fetch(`${API}/api/runs?limit=10`),
      ]);

      if (responses.some((response) => !response.ok)) {
        throw new Error("Unable to retrieve TradePulse data.");
      }

      const [stats, docs, events, monitoringRuns] =
        await Promise.all(responses.map((response) => response.json()));

      setDashboard(stats);
      setDocuments(docs);
      setChanges(events);
      setRuns(monitoringRuns);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 60000);
    return () => clearInterval(interval);
  }, []);

  function formatDate(value) {
    if (!value) return "Not available";
    return new Date(value).toLocaleDateString("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  }

  function formatTime(value) {
    if (!value) return "Not available";
    return new Date(value).toLocaleString("en-IN");
  }

  const cards = [
    {
      label: "Total Documents",
      value: dashboard?.total_documents ?? "—",
      icon: FileText,
    },
    {
      label: "Document Versions",
      value: dashboard?.total_versions ?? "—",
      icon: GitBranch,
    },
    {
      label: "Changes Detected",
      value: dashboard?.total_changes ?? "—",
      icon: Activity,
    },
    {
      label: "Monitoring Runs",
      value: dashboard?.total_runs ?? "—",
      icon: RefreshCw,
    },
  ];

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">
            <ShieldCheck size={24} />
          </div>
          <div>
            <h2>TradePulse</h2>
            <span>INTELLIGENCE</span>
          </div>
        </div>

        <div className="nav-label">WORKSPACE</div>
        <div className="nav-item active">
          <LayoutDashboard size={18} />
          Dashboard
        </div>

        <div className="sidebar-bottom">
          <div className="system-status">
            <span className="status-dot" />
            Monitoring system
            <strong>Active</strong>
          </div>
          <p>Regulatory intelligence platform</p>
          <p>TradePulse v1.0</p>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div>
            <span className="breadcrumb">WORKSPACE / OVERVIEW</span>
            <h1>Regulatory Intelligence</h1>
            <p>Monitor regulatory documents and identify changes.</p>
          </div>

          <button className="refresh-button" onClick={loadData}>
            <RefreshCw size={16} />
            Refresh data
          </button>
        </header>

        {error && <div className="error-banner">{error}</div>}

        <section className="welcome-panel">
          <div>
            <span className="eyebrow">TRADEPULSE MONITORING</span>
            <h2>Stay ahead of regulatory changes.</h2>
            <p>
              Track official DGFT notifications, preserve document versions,
              and identify changes through SHA-256 fingerprint comparison.
            </p>
          </div>
          <ShieldCheck size={54} />
        </section>

        <section className="stats-grid">
          {cards.map((card) => {
            const Icon = card.icon;
            return (
              <div className="stat-card" key={card.label}>
                <div className="stat-heading">
                  <span>{card.label}</span>
                  <Icon size={19} />
                </div>
                <strong>{loading ? "..." : card.value}</strong>
              </div>
            );
          })}
        </section>

        <section className="content-grid">
          <div className="panel documents-panel">
            <div className="panel-heading">
              <div>
                <h3>Latest Notifications</h3>
                <p>Official DGFT documents discovered by TradePulse</p>
              </div>
              <FileText size={20} />
            </div>

            {loading ? (
              <p className="empty">Loading documents...</p>
            ) : documents.length === 0 ? (
              <p className="empty">No documents available.</p>
            ) : (
              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>Notification</th>
                      <th>Title</th>
                      <th>Published</th>
                      <th>Source</th>
                    </tr>
                  </thead>
                  <tbody>
                    {documents.map((doc) => (
                      <tr key={doc.id}>
                        <td className="notice-number">{doc.notice_number}</td>
                        <td className="doc-title">{doc.title}</td>
                        <td>{formatDate(doc.publish_date)}</td>
                        <td>
                          <a
                            href={doc.document_url}
                            target="_blank"
                            rel="noreferrer"
                            className="source-link"
                          >
                            PDF <ExternalLink size={13} />
                          </a>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div className="right-column">
            <div className="panel">
              <div className="panel-heading">
                <div>
                  <h3>Detected Changes</h3>
                  <p>Document version events</p>
                </div>
                <GitBranch size={20} />
              </div>

              {changes.length === 0 ? (
                <p className="empty">No document changes detected yet.</p>
              ) : (
                changes.map((change) => (
                  <div className="event-item" key={change.id}>
                    <span className="event-dot" />
                    <div>
                      <strong>{change.notice_number}</strong>
                      <p>{change.description}</p>
                      <small>{formatTime(change.detected_at)}</small>
                    </div>
                  </div>
                ))
              )}
            </div>

            <div className="panel">
              <div className="panel-heading">
                <div>
                  <h3>Monitoring Activity</h3>
                  <p>Recent execution history</p>
                </div>
                <Clock3 size={20} />
              </div>

              {runs.length === 0 ? (
                <p className="empty">No monitoring runs available.</p>
              ) : (
                runs.map((run) => (
                  <div className="run-item" key={run.id}>
                    <div>
                      <strong>Run #{run.id}</strong>
                      <small>{formatTime(run.started_at)}</small>
                    </div>
                    <span className={`run-status ${run.status}`}>
                      {run.status}
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>
        </section>

        <footer>
          TradePulse Intelligence · Automated regulatory document monitoring
        </footer>
      </main>
    </div>
  );
}

export default App;
