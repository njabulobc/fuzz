import React, { useCallback, useEffect, useMemo, useState } from 'react'
import axios from 'axios'
import { FindingsTable } from '../components/FindingsTable'

const defaultApiUrl = (() => {
  if (typeof window === 'undefined') return 'http://localhost:8000/api'

  const origin = window.location.origin || 'http://${window.location.hostname}'
  return `${origin.replace(/\/$/, '')}/api`
})()

const API_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? defaultApiUrl

const SAMPLE_CONTRACT = `// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract SampleToken {
    string public name = "SampleToken";
    string public symbol = "SMP";
    uint8 public decimals = 18;
    uint256 public totalSupply = 1_000_000 * 10 ** uint256(decimals);

    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);

    constructor() {
        balanceOf[msg.sender] = totalSupply;
    }

    function transfer(address to, uint256 value) public returns (bool) {
        require(balanceOf[msg.sender] >= value, "Insufficient balance");
        _transfer(msg.sender, to, value);
        return true;
    }

    function approve(address spender, uint256 value) public returns (bool) {
        allowance[msg.sender][spender] = value;
        emit Approval(msg.sender, spender, value);
        return true;
    }

    function transferFrom(address from, address to, uint256 value) public returns (bool) {
        require(balanceOf[from] >= value, "Insufficient balance");
        require(allowance[from][msg.sender] >= value, "Allowance too low");
        allowance[from][msg.sender] -= value;
        _transfer(from, to, value);
        return true;
    }

    function _transfer(address from, address to, uint256 value) internal {
        require(to != address(0), "Cannot transfer to zero address");
        balanceOf[from] -= value;
        balanceOf[to] += value;
        emit Transfer(from, to, value);
    }
}
`

type Project = { id: string; name: string; path: string; meta?: Record<string, unknown>; created_at?: string }
type ScanSummary = { id: string; project_id: string; status: string; target: string; tools: string[]; started_at: string; finished_at?: string; logs?: string }
type Finding = {
  id: string
  tool: string
  title: string
  description: string
  severity: string
  category?: string
  file_path?: string
  line_number?: string
  function?: string
}
type ScanDetail = ScanSummary & { findings: Finding[] }
type QuickScanResult = { project_id: string; scan_id: string }

type Toast = { tone: 'info' | 'success' | 'error'; message: string }

const TOOLBOX = ['slither', 'mythril', 'echidna']
const PROJECT_FORM_STORAGE_KEY = 'projectForm'
const SCAN_FORM_STORAGE_KEY = 'scanForm'
const QUICK_SCAN_FORM_STORAGE_KEY = 'quickScanForm'
const SELECTED_SCAN_STORAGE_KEY = 'selectedScanId'
const DEFAULT_PROJECT_FORM = { name: '', path: '', meta: '' }
const DEFAULT_SCAN_FORM = { project_id: '', target: 'contracts/SampleToken.sol', tools: [...TOOLBOX] }
const DEFAULT_QUICK_SCAN_FORM = {
  project: { ...DEFAULT_PROJECT_FORM },
  target: DEFAULT_SCAN_FORM.target,
  tools: [...TOOLBOX],
}

const safeLoadJson = <T,>(value: string | null, fallback: T): T => {
  if (!value) return fallback
  try {
    const parsed = JSON.parse(value) as T
    return { ...fallback, ...parsed }
  } catch (error) {
    console.warn('Could not parse persisted form data', error)
    return fallback
  }
}

const App: React.FC = () => {
  const [projects, setProjects] = useState<Project[]>([])
  const [scans, setScans] = useState<ScanSummary[]>([])
  const [selectedScanId, setSelectedScanId] = useState<string>('')
  const [scanDetail, setScanDetail] = useState<ScanDetail | null>(null)
  const [loadingProjects, setLoadingProjects] = useState(false)
  const [loadingScans, setLoadingScans] = useState(false)
  const [loadingFindings, setLoadingFindings] = useState(false)
  const [projectForm, setProjectForm] = useState(DEFAULT_PROJECT_FORM)
  const [scanForm, setScanForm] = useState(DEFAULT_SCAN_FORM)
  const [quickForm, setQuickForm] = useState(DEFAULT_QUICK_SCAN_FORM)
  const [toast, setToast] = useState<Toast | null>(null)

  const showToast = (toast: Toast) => {
    setToast(toast)
    setTimeout(() => setToast(null), 4500)
  }

  const loadProjects = useCallback(async () => {
    setLoadingProjects(true)
    try {
      const res = await axios.get<Project[]>(`${API_URL}/projects`)
      setProjects(res.data)
      
      setScanForm((prev) => {
        const hasSelectedProject = res.data.some((p) => p.id === prev.project_id)

        if (res.data.length === 0) {
          return prev.project_id ? { ...prev, project_id: '' } : prev
        }

        if (!prev.project_id || !hasSelectedProject) {
          return { ...prev, project_id: res.data[0].id }
        }

        return prev
      })
    } catch (error) {
      showToast({ tone: 'error', message: 'Failed to load projects' })
    } finally {
      setLoadingProjects(false)
    }
  }, [])

  const loadScans = useCallback(async () => {
    setLoadingScans(true)
    try {
      const res = await axios.get<ScanSummary[]>(`${API_URL}/scans`)
      setScans(res.data)
    } catch (error) {
      showToast({ tone: 'error', message: 'Failed to load scans' })
    } finally {
      setLoadingScans(false)
    }
  }, [])

  const loadScanDetail = useCallback(
    async (id: string) => {
      if (!id) return
      setLoadingFindings(true)
      try {
        const res = await axios.get<ScanDetail>(`${API_URL}/scans/${id}`)
        setScanDetail(res.data)
      } catch (error) {
        showToast({ tone: 'error', message: 'Could not load scan details' })
      } finally {
        setLoadingFindings(false)
      }
    },
    []
  )

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const meta = projectForm.meta ? JSON.parse(projectForm.meta) : undefined
      const payload = { name: projectForm.name, path: projectForm.path, meta }
      const res = await axios.post<Project>(`${API_URL}/projects`, payload)
      setProjects((prev) => [...prev, res.data])
      setProjectForm(DEFAULT_PROJECT_FORM)
      showToast({ tone: 'success', message: 'Project added successfully' })
      if (!scanForm.project_id) {
        setScanForm((prev) => ({ ...prev, project_id: res.data.id }))
      }
    } catch (error) {
      showToast({ tone: 'error', message: 'Unable to create project. Check inputs.' })
    }
  }

  const handleStartScan = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const payload = { ...scanForm }
      const res = await axios.post<ScanSummary>(`${API_URL}/scans`, payload)
      showToast({ tone: 'success', message: 'Scan started. Refreshing status…' })
      setSelectedScanId(res.data.id)
      loadScans()
      loadScanDetail(res.data.id)
    } catch (error) {
      showToast({ tone: 'error', message: 'Unable to start scan. Ensure project & target exist.' })
    }
  }

  const handleQuickScan = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const meta = quickForm.project.meta ? JSON.parse(quickForm.project.meta) : undefined
      const payload = { project: { ...quickForm.project, meta }, target: quickForm.target, tools: quickForm.tools }
      const res = await axios.post<QuickScanResult>(`${API_URL}/scans/quick`, payload)
      showToast({ tone: 'success', message: 'Project provisioned and scan started.' })
      setSelectedScanId(res.data.scan_id)
      loadProjects()
      loadScans()
      loadScanDetail(res.data.scan_id)
    } catch (error) {
      showToast({ tone: 'error', message: 'Unable to quick scan. Check project details & target.' })
    }
  }

  const handleCopySample = async () => {
    try {
      await navigator.clipboard.writeText(SAMPLE_CONTRACT)
      showToast({ tone: 'success', message: 'Sample Solidity contract copied to clipboard.' })
    } catch (error) {
      showToast({ tone: 'error', message: 'Could not copy contract to clipboard.' })
    }
  }

  const handleDownloadSample = () => {
    const blob = new Blob([SAMPLE_CONTRACT], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'SampleToken.sol'
    link.click()
    URL.revokeObjectURL(url)
    showToast({ tone: 'info', message: 'SampleToken.sol downloaded. Place it in your project path.' })
  }

  useEffect(() => {
    const storedProjectForm = safeLoadJson(localStorage.getItem(PROJECT_FORM_STORAGE_KEY), DEFAULT_PROJECT_FORM)
    const storedScanForm = safeLoadJson(localStorage.getItem(SCAN_FORM_STORAGE_KEY), DEFAULT_SCAN_FORM)
    const storedQuickForm = safeLoadJson(localStorage.getItem(QUICK_SCAN_FORM_STORAGE_KEY), DEFAULT_QUICK_SCAN_FORM)
    const storedSelectedScan = localStorage.getItem(SELECTED_SCAN_STORAGE_KEY)

    setProjectForm(storedProjectForm)
    setScanForm(storedScanForm)
    setQuickForm(storedQuickForm)
    if (storedSelectedScan) setSelectedScanId(storedSelectedScan)
  }, [])

  useEffect(() => {
    localStorage.setItem(PROJECT_FORM_STORAGE_KEY, JSON.stringify(projectForm))
  }, [projectForm])

  useEffect(() => {
    localStorage.setItem(SCAN_FORM_STORAGE_KEY, JSON.stringify(scanForm))
  }, [scanForm])

  useEffect(() => {
    localStorage.setItem(QUICK_SCAN_FORM_STORAGE_KEY, JSON.stringify(quickForm))
  }, [quickForm])

  useEffect(() => {
    if (selectedScanId) {
      localStorage.setItem(SELECTED_SCAN_STORAGE_KEY, selectedScanId)
    } else {
      localStorage.removeItem(SELECTED_SCAN_STORAGE_KEY)
    }
  }, [selectedScanId])

  useEffect(() => {
    loadProjects()
    loadScans()
  }, [loadProjects, loadScans])

  useEffect(() => {
    if (selectedScanId) {
      loadScanDetail(selectedScanId)
    } else {
      setScanDetail(null)
    }
  }, [selectedScanId, loadScanDetail])

  useEffect(() => {
    if (!selectedScanId) return
    const interval = setInterval(() => {
      loadScans()
      loadScanDetail(selectedScanId)
    }, 6000)
    return () => clearInterval(interval)
  }, [selectedScanId, loadScans, loadScanDetail])

  const selectedFindings = useMemo(() => scanDetail?.findings ?? [], [scanDetail])

  const badgeClass = (status: string) => {
    switch (status) {
      case 'SUCCESS':
        return 'bg-emerald-50 text-emerald-700 border-emerald-100'
      case 'RUNNING':
        return 'bg-sky-50 text-sky-700 border-sky-100'
      case 'FAILED':
        return 'bg-rose-50 text-rose-700 border-rose-100'
      default:
        return 'bg-slate-100 text-slate-700 border-slate-200'
    }
  }

  const cardClass = 'bg-white border border-slate-200 shadow-card rounded-xl p-6'
  const inputClass =
    'w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus:border-sky-400 focus:outline-none focus:ring-2 focus:ring-sky-100'
  const labelClass = 'text-sm font-semibold text-slate-700'
  const buttonPrimary =
    'inline-flex items-center justify-center gap-2 rounded-lg bg-sky-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-sky-700 focus:outline-none focus:ring-2 focus:ring-sky-200'
  const buttonSecondary =
    'inline-flex items-center justify-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-800 shadow-sm transition hover:border-slate-300 focus:outline-none focus:ring-2 focus:ring-slate-100'

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="mx-auto max-w-6xl px-4 py-10">
        <header className="mb-6 flex flex-col gap-4 rounded-2xl bg-gradient-to-r from-sky-600 via-sky-500 to-indigo-500 p-6 text-white shadow-card">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.18em] text-sky-100">Smart contract fuzzer</p>
              <h1 className="text-3xl font-semibold">Security workflow dashboard</h1>
              <p className="mt-2 text-sky-100">Track scan runs, findings, and seed a sample Solidity contract.</p>
            </div>
            <button
              className="rounded-full border border-white/30 bg-white/20 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-white/30"
              onClick={() => {
                loadProjects()
                loadScans()
                if (selectedScanId) loadScanDetail(selectedScanId)
              }}
            >
              Refresh data
            </button>
          </div>
          {toast && (
            <div
              className={`w-full rounded-xl border px-4 py-3 text-sm shadow-sm ${
                toast.tone === 'error'
                  ? 'border-rose-200 bg-rose-50 text-rose-800'
                  : toast.tone === 'success'
                  ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
                  : 'border-sky-200 bg-sky-50 text-sky-800'
              }`}
            >
              {toast.message}
            </div>
          )}
        </header>

        <div className="grid grid-cols-1 gap-5 lg:grid-cols-[1.1fr_0.9fr]">
          <section className={cardClass}>
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-900">Projects</h2>
              {loadingProjects && <span className="text-xs text-slate-500">Loading…</span>}
            </div>

            {projects.length === 0 ? (
              <p className="text-sm text-slate-600">No projects yet. Add one below to start scanning.</p>
            ) : (
              <ul className="grid gap-3">
                {projects.map((p) => (
                  <li key={p.id} className="rounded-lg border border-slate-200 bg-slate-50/70 px-4 py-3">
                    <div className="font-semibold text-slate-900">{p.name}</div>
                    <div className="text-sm text-slate-600">{p.path}</div>
                    {p.meta && <div className="text-xs text-slate-500">Meta: {JSON.stringify(p.meta)}</div>}
                  </li>
                ))}
              </ul>
            )}

            <form onSubmit={handleCreateProject} className="mt-6 grid gap-4">
              <div className="grid gap-2">
                <label className={labelClass}>Project name</label>
                <input
                  required
                  value={projectForm.name}
                  onChange={(e) => setProjectForm((prev) => ({ ...prev, name: e.target.value }))}
                  placeholder="ex: sample-audits"
                  className={inputClass}
                />
              </div>
              <div className="grid gap-2">
                <label className={labelClass}>Path to contracts (used as scan target root)</label>
                <input
                  required
                  value={projectForm.path}
                  onChange={(e) => setProjectForm((prev) => ({ ...prev, path: e.target.value }))}
                  placeholder="/workspace/contracts"
                  className={inputClass}
                />
              </div>
              <div className="grid gap-2">
                <label className={labelClass}>Meta (JSON optional)</label>
                <textarea
                  value={projectForm.meta}
                  onChange={(e) => setProjectForm((prev) => ({ ...prev, meta: e.target.value }))}
                  placeholder='{"network": "sepolia"}'
                  rows={2}
                  className={`${inputClass} resize-y`}
                />
              </div>
              <div className="flex justify-end">
                <button type="submit" className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-emerald-700 focus:outline-none focus:ring-2 focus:ring-emerald-200">
                  Add project
                </button>
              </div>
            </form>
          </section>

          <section className={cardClass}>
            <h2 className="text-lg font-semibold text-slate-900">Start a scan</h2>
            <p className="mt-1 text-sm text-slate-600">Pick a project, choose tools, and provide a target path. Status updates every few seconds once started.</p>

            <form onSubmit={handleStartScan} className="mt-4 grid gap-4">
              <div className="grid gap-2">
                <label className={labelClass}>Project</label>
                <select
                  required
                  value={scanForm.project_id}
                  onChange={(e) => setScanForm((prev) => ({ ...prev, project_id: e.target.value }))}
                  className={inputClass}
                >
                  <option value="" disabled>
                    Select a project
                  </option>
                  {projects.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid gap-2">
                <label className={labelClass}>Tools</label>
                <div className="flex flex-wrap gap-2">
                  {TOOLBOX.map((tool) => {
                    const isSelected = scanForm.tools.includes(tool)
                    return (
                      <button
                        type="button"
                        key={tool}
                        onClick={() =>
                          setScanForm((prev) => ({
                            ...prev,
                            tools: isSelected ? prev.tools.filter((t) => t !== tool) : [...prev.tools, tool],
                          }))
                        }
                        className={`${
                          isSelected
                            ? 'border-sky-400 bg-sky-50 text-sky-700'
                            : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300'
                        } rounded-full border px-3 py-1 text-xs font-semibold transition`}
                      >
                        {tool}
                      </button>
                    )
                  })}
                </div>
              </div>

              <div className="grid gap-2">
                <label className={labelClass}>Target path</label>
                <input
                  required
                  value={scanForm.target}
                  onChange={(e) => setScanForm((prev) => ({ ...prev, target: e.target.value }))}
                  placeholder="contracts/SampleToken.sol"
                  className={inputClass}
                />
              </div>

              <div className="flex justify-end gap-3">
                <button type="submit" className={buttonPrimary}>
                  Start scan
                </button>
              </div>
            </form>

            <div className="mt-6 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
              <h3 className="text-sm font-semibold text-slate-900">New to the workflow?</h3>
              <p className="mt-1 text-sm text-slate-600">
                Use this starter file to validate the workflow. Download or copy it, place it under your project path (e.g. <code className="rounded bg-slate-200 px-1 py-0.5 text-xs">contracts/SampleToken.sol</code>), then run a scan against that path.
              </p>
              <div className="mt-3 flex flex-wrap gap-3">
                <button onClick={handleCopySample} className={buttonSecondary} type="button">
                  Copy contract
                </button>
                <button onClick={handleDownloadSample} className={buttonPrimary} type="button">
                  Download SampleToken.sol
                </button>
              </div>
            </div>
          </section>
        </div>

        <section className={`${cardClass} mt-5`}>
          <h2 className="text-lg font-semibold text-slate-900">Quick scan</h2>
          <p className="mt-1 text-sm text-slate-600">
            Create a project and start a scan in one go. Use this when onboarding a new codebase.
          </p>

          <form onSubmit={handleQuickScan} className="mt-4 grid gap-4 md:grid-cols-2">
            <div className="grid gap-2">
              <label className={labelClass}>Project name</label>
              <input
                required
                value={quickForm.project.name}
                onChange={(e) =>
                  setQuickForm((prev) => ({ ...prev, project: { ...prev.project, name: e.target.value } }))
                }
                placeholder="ex: onboarding-audit"
                className={inputClass}
              />
            </div>

            <div className="grid gap-2">
              <label className={labelClass}>Project path</label>
              <input
                required
                value={quickForm.project.path}
                onChange={(e) =>
                  setQuickForm((prev) => ({ ...prev, project: { ...prev.project, path: e.target.value } }))
                }
                placeholder="/workspace/contracts"
                className={inputClass}
              />
            </div>

            <div className="grid gap-2 md:col-span-2">
              <label className={labelClass}>Meta (JSON optional)</label>
              <textarea
                value={quickForm.project.meta}
                onChange={(e) =>
                  setQuickForm((prev) => ({ ...prev, project: { ...prev.project, meta: e.target.value } }))
                }
                placeholder='{"network": "local"}'
                rows={2}
                className={`${inputClass} resize-y`}
              />
            </div>

            <div className="grid gap-2">
              <label className={labelClass}>Target path</label>
              <input
                required
                value={quickForm.target}
                onChange={(e) => setQuickForm((prev) => ({ ...prev, target: e.target.value }))}
                placeholder="contracts/SampleToken.sol"
                className={inputClass}
              />
            </div>

            <div className="grid gap-2">
              <label className={labelClass}>Tools</label>
              <div className="flex flex-wrap gap-2">
                {TOOLBOX.map((tool) => {
                  const isSelected = quickForm.tools.includes(tool)
                  return (
                    <button
                      type="button"
                      key={tool}
                      onClick={() =>
                        setQuickForm((prev) => ({
                          ...prev,
                          tools: isSelected ? prev.tools.filter((t) => t !== tool) : [...prev.tools, tool],
                        }))
                      }
                      className={`${
                        isSelected
                          ? 'border-sky-400 bg-sky-50 text-sky-700'
                          : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300'
                      } rounded-full border px-3 py-1 text-xs font-semibold transition`}
                    >
                      {tool}
                    </button>
                  )
                })}
              </div>
            </div>

            <div className="md:col-span-2 flex justify-end gap-3">
              <button type="submit" className={buttonPrimary}>
                Provision project & start scan
              </button>
            </div>
          </form>
        </section>

        <section className={`${cardClass} mt-5`}>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">Scan history</h2>
              <p className="text-sm text-slate-600">Select a run to view live findings and logs.</p>
            </div>
            {loadingScans && <span className="text-xs text-slate-500">Updating…</span>}
          </div>

          <div className="mt-3 overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-3 py-2">Status</th>
                  <th className="px-3 py-2">Project</th>
                  <th className="px-3 py-2">Target</th>
                  <th className="px-3 py-2">Tools</th>
                  <th className="px-3 py-2">Started</th>
                  <th className="px-3 py-2">Finished</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {scans.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-3 py-4 text-center text-slate-500">
                      No scans yet. Kick off a scan to see live feedback.
                    </td>
                  </tr>
                )}
                {scans.map((scan) => (
                  <tr
                    key={scan.id}
                    onClick={() => setSelectedScanId(scan.id)}
                    className={`${
                      selectedScanId === scan.id ? 'bg-indigo-50/60' : 'bg-white'
                    } cursor-pointer transition hover:bg-slate-50`}
                  >
                    <td className="px-3 py-3">
                      <span className={`inline-flex rounded-full border px-3 py-1 text-[11px] font-bold uppercase ${badgeClass(scan.status)}`}>
                        {scan.status}
                      </span>
                    </td>
                    <td className="px-3 py-3 font-semibold text-slate-800">{scan.project_id}</td>
                    <td className="px-3 py-3 text-slate-700">{scan.target}</td>
                    <td className="px-3 py-3 text-slate-700">{scan.tools.join(', ')}</td>
                    <td className="px-3 py-3 text-slate-600">{new Date(scan.started_at).toLocaleString()}</td>
                    <td className="px-3 py-3 text-slate-600">{scan.finished_at ? new Date(scan.finished_at).toLocaleString() : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {selectedScanId && (
          <section className={`${cardClass} mt-5`}>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold text-slate-900">Findings for scan {selectedScanId}</h2>
                <p className="text-sm text-slate-600">
                  Severity and tool filters are available below. {loadingFindings && 'Refreshing findings…'}
                </p>
              </div>
              <button onClick={() => loadScanDetail(selectedScanId)} className={buttonSecondary} type="button">
                Reload findings
              </button>
            </div>

            <FindingsTable findings={selectedFindings} />

            {scanDetail?.logs && (
              <div className="mt-4">
                <h3 className="mb-2 text-base font-semibold text-slate-900">Worker feedback</h3>
                <pre className="max-h-64 overflow-x-auto rounded-lg bg-slate-900 p-4 text-sm text-slate-100">{scanDetail.logs}</pre>
              </div>
            )}
          </section>
        )}
      </div>
    </div>
  )
}

export default App
