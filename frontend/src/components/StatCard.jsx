export default function StatCard({ label, value, accent }) {
    return (
        <div className={`stat-card ${accent ? `stat-card--${accent}` : ""}`}>
            <span className="stat-card__value">{value ?? "—"}</span>
            <span className="stat-card__label">{label}</span>
        </div>
    );
}
