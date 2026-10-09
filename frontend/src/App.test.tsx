import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import App from './App'
import { fullAnalysis, toolchain } from './test/fixtures'
import type { FullAnalysis, ToolchainInfo } from './types/api'

const SAMPLES = [
  { id: 'constant_expr', title: 'Arithmetic & constant expressions', language: 'c', description: '', source: 'int main(void){ return 10 + 20; }' },
  { id: 'cuda_kernel', title: 'CUDA kernels (PTX)', language: 'cuda', description: '', source: '__global__ void k() {}' },
]

type Handler = (body: unknown) => { status?: number; json: unknown } | Promise<{ status?: number; json: unknown }>

function mockBackend(opts: { tc?: ToolchainInfo; full?: Handler; optimization?: Handler } = {}) {
  const calls: { url: string; body: unknown }[] = []
  const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
    const body = init?.body ? JSON.parse(init.body as string) : undefined
    calls.push({ url, body })
    const respond = (r: { status?: number; json: unknown }) =>
      new Response(JSON.stringify(r.json), { status: r.status ?? 200, headers: { 'Content-Type': 'application/json' } })
    if (url.endsWith('/toolchain')) return respond({ json: opts.tc ?? toolchain() })
    if (url.endsWith('/samples')) return respond({ json: SAMPLES })
    if (url.endsWith('/analyze/full')) return respond(await (opts.full ?? (() => ({ json: fullAnalysis() })))(body))
    if (url.endsWith('/analyze/optimization')) return respond(await opts.optimization!(body))
    return respond({ status: 404, json: { error: { code: 'nf', message: 'not found' } } })
  })
  vi.stubGlobal('fetch', fetchMock)
  return calls
}

async function renderApp() {
  render(<App />)
  await screen.findByText(/clang version 23\.1\.3/)
}

beforeEach(() => vi.unstubAllGlobals())
afterEach(() => vi.restoreAllMocks())

describe('GPUForge app', () => {
  it('lets the user edit source and submits it with the selected settings', async () => {
    const calls = mockBackend()
    await renderApp()
    fireEvent.change(screen.getByTestId('source-editor'), { target: { value: 'int main(void){return 7;}' } })
    fireEvent.change(screen.getByLabelText('Optimization level'), { target: { value: 'O2' } })
    fireEvent.click(screen.getByRole('button', { name: 'Compile & Analyze' }))
    await screen.findByRole('tab', { name: /Tokens/, selected: true })
    const req = calls.find((c) => c.url.endsWith('/analyze/full'))!.body as Record<string, string>
    expect(req).toMatchObject({ source: 'int main(void){return 7;}', language: 'c', opt_level: 'O2', target: 'cpu' })
  })

  it('loads a sample program into the editor and switches language', async () => {
    mockBackend()
    await renderApp()
    fireEvent.change(screen.getByLabelText('Sample program'), { target: { value: 'cuda_kernel' } })
    expect(screen.getByTestId('source-editor')).toHaveValue('__global__ void k() {}')
    expect(screen.getByLabelText('Language')).toHaveValue('cuda')
    expect(screen.getByRole('radio', { name: 'NVIDIA PTX' })).toHaveAttribute('aria-checked', 'true')
  })

  it('shows a loading state while compiling', async () => {
    let release!: () => void
    mockBackend({ full: () => new Promise((r) => { release = () => r({ json: fullAnalysis() }) }) })
    await renderApp()
    fireEvent.click(screen.getByRole('button', { name: 'Compile & Analyze' }))
    expect(await screen.findByRole('status')).toHaveTextContent(/Running Clang/)
    expect(screen.getByRole('button', { name: 'Compiling…' })).toBeDisabled()
    await act(async () => release())
    await waitFor(() => expect(screen.queryByRole('status')).not.toBeInTheDocument())
  })

  it('shows an error state with the backend message', async () => {
    mockBackend({ full: () => ({ status: 504, json: { error: { code: 'compiler_timeout', message: "'clang' did not finish within 20 s" } } }) })
    await renderApp()
    fireEvent.click(screen.getByRole('button', { name: 'Compile & Analyze' }))
    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('Analysis failed')
    expect(alert).toHaveTextContent('did not finish within 20 s')
  })

  it('switches phases and displays each phase output', async () => {
    mockBackend()
    await renderApp()
    fireEvent.click(screen.getByRole('button', { name: 'Compile & Analyze' }))
    await screen.findByText('identifier')

    fireEvent.click(screen.getByRole('tab', { name: /AST/ }))
    expect(await screen.findByText('FunctionDecl')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('tab', { name: /^IR/ }))
    expect(screen.getByTestId('code-view')).toHaveValue('define i32 @main() {\n  %1 = alloca i32\n  ret i32 30\n}')
    expect(screen.getByText('Reserves stack space.')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('tab', { name: /Assembly/ }))
    expect(screen.getByText(/x86_64-pc-windows-msvc/, { selector: 'span' })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('tab', { name: /Report/ }))
    expect(screen.getByText('Unavailable')).toBeInTheDocument()

    // The pipeline diagram selects phases too.
    fireEvent.click(within(screen.getByTestId('pipeline')).getByText('node:Semantic Diagnostics'))
    expect(screen.getByRole('tab', { name: /Diagnostics/ })).toHaveAttribute('aria-selected', 'true')
  })

  it('renders the optimization comparison and re-runs it with passes', async () => {
    const calls = mockBackend({
      optimization: () => {
        const o = fullAnalysis().optimization
        return { json: { ...o, mode: 'passes', optimized_label: 'after mem2reg', observations: ['mem2reg removed 1 alloca'] } }
      },
    })
    await renderApp()
    fireEvent.click(screen.getByRole('button', { name: 'Compile & Analyze' }))
    await screen.findByText('identifier')
    fireEvent.click(screen.getByRole('tab', { name: /Optimize/ }))

    expect(screen.getByText(/all 1 `alloca` stack slots were eliminated/)).toBeInTheDocument()
    expect(screen.getByText('SROA')).toBeInTheDocument()
    // The removed alloca appears only in the left (baseline) column, marked with '-'.
    const removed = screen.getAllByRole('cell').filter((td) => td.textContent?.includes('%1 = alloca i32'))
    expect(removed).toHaveLength(1)
    expect(removed[0].textContent?.trimStart().startsWith('-')).toBe(true)

    fireEvent.click(screen.getByRole('button', { name: 'Run passes' }))
    fireEvent.change(screen.getByLabelText('Add pass'), { target: { value: 'mem2reg' } })
    fireEvent.click(screen.getByRole('button', { name: 'Run comparison' }))
    expect(await screen.findByText('mem2reg removed 1 alloca')).toBeInTheDocument()
    const req = calls.find((c) => c.url.endsWith('/analyze/optimization'))!.body as { passes: string[] }
    expect(req.passes).toEqual(['mem2reg'])

    fireEvent.click(screen.getByRole('button', { name: 'Raw before/after' }))
    expect(screen.getByTestId('diff-editor')).toHaveTextContent('ret i32 30')
  })

  it('explains missing toolchains instead of showing fake output', async () => {
    const result: FullAnalysis = fullAnalysis()
    result.ptx = { ...result.ptx, message: 'No PTX toolchain found: install the CUDA Toolkit (nvcc) or an LLVM build with the NVPTX target.' }
    mockBackend({
      tc: toolchain({ ptx_method: null, nvptx_backend: false, capabilities: { ...toolchain().capabilities, ptx: false } }),
      full: () => ({ json: result }),
    })
    await renderApp()
    expect(screen.getByRole('radio', { name: 'NVIDIA PTX' })).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: 'Compile & Analyze' }))
    await screen.findByText('identifier')
    fireEvent.click(screen.getByRole('tab', { name: /PTX/ }))
    expect(screen.getByText(/No PTX toolchain found/)).toBeInTheDocument()
    expect(screen.getByText(/none detected/)).toBeInTheDocument()
    expect(screen.queryByTestId('code-view')).not.toBeInTheDocument()
  })

  it('disables compilation when Clang is missing', async () => {
    mockBackend({ tc: toolchain({ clang: { name: 'clang', available: false, path: null, version: null, error: 'clang was not found' } }) })
    render(<App />)
    await waitFor(() => expect(screen.getByRole('button', { name: 'Compile & Analyze' })).toBeDisabled())
    fireEvent.click(screen.getByRole('button', { name: 'Toolchain' }))
    expect(screen.getByRole('dialog')).toHaveTextContent('clang was not found')
  })

  it('shows a clear message when the backend is down', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => { throw new TypeError('Failed to fetch') }))
    render(<App />)
    expect(await screen.findByText(/Cannot reach the GPUForge backend/)).toBeInTheDocument()
  })
})
