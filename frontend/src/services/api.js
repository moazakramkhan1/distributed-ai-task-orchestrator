const BASE = "/api";

export async function fetchQueueMetrics() {
    const res = await fetch(`${BASE}/metrics/queue`);
    if (!res.ok) throw new Error("Failed to fetch queue metrics");
    return res.json();
}

export async function fetchHealth() {
    const res = await fetch(`${BASE}/health/detailed`);
    if (!res.ok) throw new Error("Failed to fetch health");
    return res.json();
}

export async function fetchResults(limit = 20) {
    const res = await fetch(`${BASE}/metrics/results?limit=${limit}`);
    if (!res.ok) throw new Error("Failed to fetch results");
    return res.json();
}

export async function fetchWorkerMetrics() {
    const res = await fetch(`${BASE}/metrics/workers`);
    if (!res.ok) throw new Error("Failed to fetch worker metrics");
    return res.json();
}
