import type {
  ApiErrorBody, FullAnalysis, OptimizationRequest, OptimizationResponse, PTXResponse, Sample,
  SourceRequest, ToolchainInfo,
} from '../types/api'

/** An error returned by the backend (or a network failure), with a user-facing message. */
export class ApiError extends Error {
  readonly status: number
  readonly code: string

  constructor(status: number, code: string, message: string) {
    super(message)
    this.status = status
    this.code = code
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(`/api${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    })
  } catch {
    throw new ApiError(0, 'network_error',
      'Cannot reach the GPUForge backend. Is it running on http://127.0.0.1:8000?')
  }
  if (!res.ok) {
    let body: ApiErrorBody | null = null
    try { body = await res.json() } catch { /* non-JSON error */ }
    const details = body?.error.details?.map((d) => `${d.field}: ${d.message}`).join('; ')
    throw new ApiError(
      res.status,
      body?.error.code ?? 'http_error',
      (body?.error.message ?? `Request failed with HTTP ${res.status}`) + (details ? ` (${details})` : ''),
    )
  }
  return res.json() as Promise<T>
}

const post = <T>(path: string, body: unknown) =>
  request<T>(path, { method: 'POST', body: JSON.stringify(body) })

export const api = {
  toolchain: () => request<ToolchainInfo>('/toolchain'),
  refreshToolchain: () => request<ToolchainInfo>('/toolchain/refresh', { method: 'POST' }),
  samples: () => request<Sample[]>('/samples'),
  analyzeFull: (req: SourceRequest) => post<FullAnalysis>('/analyze/full', req),
  optimization: (req: OptimizationRequest) => post<OptimizationResponse>('/analyze/optimization', req),
  ptx: (req: SourceRequest & { compare_opt_level?: string | null }) => post<PTXResponse>('/compile/ptx', req),
}
