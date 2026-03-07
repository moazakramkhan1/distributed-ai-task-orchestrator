const STATUS_LABELS = {
    idle: "Idle",
    stable: "Stable",
    scaling_up: "Scaling Up",
    scaling_down: "Scaling Down",
    degraded: "Degraded",
};

export default function AutoscalingPanel({ metrics }) {
    if (!metrics) return <div className="autoscaling-panel loading">Loading worker metrics…</div>;

    const { desired_replicas, available_replicas, ready_replicas, queue_depth, scaling_status, min_replicas, max_replicas, k8s_available } = metrics;

    const statusClass = `scaling-status scaling-status--${scaling_status ?? "degraded"}`;

    return (
        <div className="autoscaling-panel">
            <div className="autoscaling-header">
                <span className={statusClass}>{STATUS_LABELS[scaling_status] ?? "Unknown"}</span>
                {!k8s_available && <span className="k8s-warning">K8s unavailable — showing estimates</span>}
            </div>

            <div className="autoscaling-grid">
                <div className="autoscaling-stat">
                    <span className="autoscaling-stat__label">Desired</span>
                    <span className="autoscaling-stat__value">{desired_replicas ?? "—"}</span>
                </div>
                <div className="autoscaling-stat">
                    <span className="autoscaling-stat__label">Available</span>
                    <span className="autoscaling-stat__value">{available_replicas ?? "—"}</span>
                </div>
                <div className="autoscaling-stat">
                    <span className="autoscaling-stat__label">Ready</span>
                    <span className="autoscaling-stat__value">{ready_replicas ?? "—"}</span>
                </div>
                <div className="autoscaling-stat">
                    <span className="autoscaling-stat__label">Queue Depth</span>
                    <span className="autoscaling-stat__value">{queue_depth ?? "—"}</span>
                </div>
                <div className="autoscaling-stat">
                    <span className="autoscaling-stat__label">Min Replicas</span>
                    <span className="autoscaling-stat__value">{min_replicas ?? "—"}</span>
                </div>
                <div className="autoscaling-stat">
                    <span className="autoscaling-stat__label">Max Replicas</span>
                    <span className="autoscaling-stat__value">{max_replicas ?? "—"}</span>
                </div>
            </div>
        </div>
    );
}
