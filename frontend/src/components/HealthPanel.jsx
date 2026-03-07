const STATUS_COLOR = {
    ok: "green",
    connected: "green",
    down: "red",
    degraded: "orange",
};

function Indicator({ status }) {
    const color = STATUS_COLOR[status] ?? "gray";
    return (
        <span className="health-indicator" style={{ color }}>
            ● {status}
        </span>
    );
}

export default function HealthPanel({ health }) {
    if (!health) return <p className="dimmed">Loading health…</p>;
    return (
        <div className="health-panel">
            {Object.entries(health).map(([key, value]) => (
                <div key={key} className="health-row">
                    <span className="health-label">{key}</span>
                    <Indicator status={value} />
                </div>
            ))}
        </div>
    );
}
