import { NextRequest, NextResponse } from "next/server";
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

export async function GET(request: NextRequest) {
  // Record this metrics request
  const end = httpRequestDuration.startTimer({ method: "GET", route: "/api/metrics" });

  try {
    const metrics = await register.metrics();
    httpRequestCounter.inc({ method: "GET", route: "/api/metrics", status: 200 });

    return new NextResponse(metrics, {
      headers: {
        "Content-Type": register.contentType,
      },
    });
  } catch (error) {
    httpRequestCounter.inc({ method: "GET", route: "/api/metrics", status: 500 });
    return NextResponse.json({ error: "Failed to collect metrics" }, { status: 500 });
  } finally {
    end();
  }
}

// Export helper functions for use in other parts of the app
export { httpRequestCounter, httpRequestDuration, activeUsersGauge, register };