import client from "prom-client";

// Create a Registry to hold metrics
const register = new client.Registry();

// Add default metrics (CPU, memory, etc.)
client.collectDefaultMetrics({ register });

// Custom metrics
const httpRequestCounter = new client.Counter({
  name: "nextjs_http_requests_total",
  help: "Total number of HTTP requests",
  labelNames: ["method", "route", "status"],
  registers: [register],
});

const httpRequestDuration = new client.Histogram({
  name: "nextjs_http_request_duration_seconds",
  help: "Duration of HTTP requests in seconds",
  labelNames: ["method", "route"],
  buckets: [0.01, 0.05, 0.1, 0.5, 1, 2, 5],
  registers: [register],
});

const activeUsersGauge = new client.Gauge({
  name: "nextjs_active_users",
  help: "Number of active users",
  labelNames: ["method"],
  registers: [register],
});

export { register, httpRequestCounter, httpRequestDuration, activeUsersGauge };