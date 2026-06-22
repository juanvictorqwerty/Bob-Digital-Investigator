import { NextRequest, NextResponse } from "next/server";
import { register, httpRequestCounter, httpRequestDuration } from "@/lib/metrics";

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
