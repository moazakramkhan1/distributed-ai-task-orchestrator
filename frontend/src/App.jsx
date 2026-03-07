import { useEffect, useState } from "react";
import AutoscalingPanel from "./components/AutoscalingPanel";
import HealthPanel from "./components/HealthPanel";
import ResultLog from "./components/ResultLog";
import StatCard from "./components/StatCard";
import { fetchHealth, fetchQueueMetrics, fetchResults, fetchWorkerMetrics } from "./services/api";
import "./index.css";

const POLL_INTERVAL = 4000;

export default function App() {
    const [queue, setQueue] = useState(null);
    const [health, setHealth] = useState(null);
    const [results, setResults] = useState(null);
    const [workerMetrics, setWorkerMetrics] = useState(null);
    const [error, setError] = useState(null);
    const [lastUpdated, setLastUpdated] = useState(null);

    async function refresh() {
        try {
            const [q, h, r, w] = await Promise.all([
                fetchQueueMetrics(),
                fetchHealth(),
                fetchResults(20),
                fetchWorkerMetrics(),
            ]);
            setQueue(q);
            setHealth(h);
            setResults(r);
            setWorkerMetrics(w);
            setError(null);
            setLastUpdated(new Date());
        } catch (err) {
            setError(err.message);
        }
    }

    useEffect(() => {
        refresh();
        const id = setInterval(refresh, POLL_INTERVAL);
        return () => clearInterval(id);
    }, []);

    return (
        <div className="app">
            <header className="app-header">
                <h1>AI Task Orchestrator</h1>
                {lastUpdated && (
                    <span className="dimmed">
                        Last updated: {lastUpdated.toLocaleTimeString()}
                    </span>
                )}
            </header>

            {error && <div className="error-banner">⚠ {error}</div>}

            <section className="section">
                <h2>Queue Status</h2>
                <div className="stat-grid">
                    <StatCard label="Pending" value={queue?.pending} accent="pending" />
                    <StatCard label="In Progress" value={queue?.in_progress} accent="progress" />
                    <StatCard label="Completed" value={queue?.completed} accent="completed" />
                    <StatCard label="Failed" value={queue?.failed} accent="failed" />
                    <StatCard label="Total" value={queue?.total} />
                </div>
            </section>

            <section className="section">
                <h2>System Health</h2>
                <HealthPanel health={health} />
            </section>

            <section className="section">
                <h2>Worker Autoscaling</h2>
                <AutoscalingPanel metrics={workerMetrics} />
            </section>

            <section className="section">
                <h2>Completed Tasks</h2>
                <ResultLog tasks={results} />
            </section>
        </div>
    );
}
