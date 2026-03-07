function truncate(str, n = 60) {
    if (!str) return "—";
    return str.length > n ? str.slice(0, n) + "…" : str;
}

const STATUS_CLASS = {
    PENDING: "badge badge--pending",
    IN_PROGRESS: "badge badge--progress",
    COMPLETED: "badge badge--completed",
    FAILED: "badge badge--failed",
};

export default function ResultLog({ tasks }) {
    if (!tasks) return <p className="dimmed">Loading results…</p>;
    if (tasks.length === 0) return <p className="dimmed">No completed tasks yet.</p>;

    return (
        <div className="result-log-wrapper">
            <table className="result-log">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Input</th>
                        <th>Status</th>
                        <th>Retries</th>
                        <th>Result</th>
                        <th>Updated</th>
                    </tr>
                </thead>
                <tbody>
                    {tasks.map((t) => (
                        <tr key={t.id}>
                            <td className="mono">{t.id.slice(0, 8)}…</td>
                            <td>{truncate(t.input_text)}</td>
                            <td>
                                <span className={STATUS_CLASS[t.status] ?? "badge"}>
                                    {t.status}
                                </span>
                            </td>
                            <td>{t.retry_count}</td>
                            <td>{truncate(t.result, 80)}</td>
                            <td className="mono">{new Date(t.updated_at).toLocaleTimeString()}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
