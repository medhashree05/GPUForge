import { useCallback, useEffect, useState } from 'react'
import { api, ApiError } from '../services/api'
import type { FullAnalysis, Sample, SourceRequest, ToolchainInfo } from '../types/api'

export function useToolchain() {
  const [toolchain, setToolchain] = useState<ToolchainInfo | null>(null)
  const [samples, setSamples] = useState<Sample[]>([])
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async (refresh = false) => {
    try {
      const [tc, s] = await Promise.all([refresh ? api.refreshToolchain() : api.toolchain(), api.samples()])
      setToolchain(tc)
      setSamples(s)
      setError(null)
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e))
    }
  }, [])

  useEffect(() => { void load() }, [load])
  return { toolchain, samples, error, reload: load }
}

export function useAnalysis() {
  const [result, setResult] = useState<FullAnalysis | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const run = useCallback(async (req: SourceRequest): Promise<FullAnalysis | null> => {
    setLoading(true)
    setError(null)
    try {
      const r = await api.analyzeFull(req)
      setResult(r)
      return r
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e))
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  return { result, setResult, loading, error, run }
}
