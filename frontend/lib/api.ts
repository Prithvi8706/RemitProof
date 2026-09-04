import type {
  BenchmarkCasesData,
  BenchmarkData,
  DashboardData,
  ExceptionDetail,
  ExceptionSummary,
} from "@/lib/types";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? process.env.API_URL ?? "http://127.0.0.1:8001";

export class ApiError extends Error {
  readonly status: number;
  readonly path: string;

  constructor(status: number, path: string) {
    super("RemitProof API returned " + status + " for " + path);
    this.name = "ApiError";
    this.status = status;
    this.path = path;
  }
}

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, { cache: "no-store" });
  if (!response.ok) {
    throw new ApiError(response.status, path);
  }
  return (await response.json()) as T;
}

export function getDashboard(): Promise<DashboardData> {
  return getJson<DashboardData>("/api/dashboard");
}

export function getBenchmark(): Promise<BenchmarkData> {
  return getJson<BenchmarkData>("/api/benchmark");
}

export function getBenchmarkCases(): Promise<BenchmarkCasesData> {
  return getJson<BenchmarkCasesData>("/api/benchmark/cases");
}

export async function getConsistentBenchmarkPublication(
  maxAttempts = 3,
): Promise<{ benchmark: BenchmarkData; caseData: BenchmarkCasesData }> {
  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    const [benchmark, caseData] = await Promise.all([getBenchmark(), getBenchmarkCases()]);
    if (benchmark.evaluation_generation_id === caseData.evaluation_generation_id) {
      return { benchmark, caseData };
    }
  }
  throw new Error("Benchmark publication changed while it was being loaded");
}

export function getException(paymentId: string): Promise<ExceptionDetail> {
  return getJson<ExceptionDetail>(`/api/exceptions/${encodeURIComponent(paymentId)}`);
}

export function getExceptions(): Promise<ExceptionSummary[]> {
  return getJson<ExceptionSummary[]>("/api/exceptions");
}
