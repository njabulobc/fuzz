import React, { useCallback, useEffect, useMemo, useState } from 'react'
import axios from 'axios'
import { FindingsTable } from '../components/FindingsTable'

const API_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000/api'

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

type Toast = { tone: 'info' | 'success' | 'error'; message: string }

const TOOLBOX = ['slither', 'mythril', 'echidna']

const App: React.FC = () => {
  const [projects, setProjects] = useState<Project[]>([])
  const [scans, setScans] = useState<ScanSummary[]>([])
  const [selectedScanId, setSelectedScanId] = useState<string>('')
  const [scanDetail, setScanDetail] = useState<ScanDetail | null>(null)
  const [loadingProjects, setLoadingProjects] = useState(false)
  const [loadingScans, setLoadingScans] = useState(false)
  const [loadingFindings, setLoadingFindings] = useState(false)
  const [projectForm, setProjectForm] = useState({ name: '', path: '', meta: '' })
  const [scanForm, setScanForm] = useState({ project_id: '', target: 'contracts/SampleToken.sol', tools: [...TOOLBOX] })
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
      if (!scanForm.project_id && res.data.length > 0) {
        setScanForm((prev) => ({ ...prev, project_id: res.data[0].id }))
      }
    } catch (error) {
      showToast({ tone: 'error', message: 'Failed to load projects' })
    } finally {
      setLoadingProjects(false)
    }
  }, [scanForm.project_id])

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
      setProjectForm({ name: '', path: '', meta: '' })
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

  const badgeColor = (status: string) => {
    switch (status) {
      case 'SUCCESS':
        return '#d1fae5'
      case 'RUNNING':
        return '#e0f2fe'
      case 'FAILED':
        return '#fee2e2'
      default:
        return '#f3f4f6'
    }
  }

  const sectionStyle: React.CSSProperties = {
    background: '#fff',
    padding: '1.25rem',
    borderRadius: '12px',
    boxShadow: '0 8px 20px rgba(0,0,0,0.04)',
    marginBottom: '1rem',
    border: '1px solid #e5e7eb',
  }

  return (
    <div style={{ padding: '2rem', fontFamily: 'Inter, system-ui, sans-serif', background: '#f8fafc', minHeight: '100vh' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <p style={{ color: '#64748b', marginBottom: '0.2rem', letterSpacing: '0.08em', fontSize: 12 }}>SMART CONTRACT FUZZER</p>
          <h1 style={{ margin: 0, fontSize: '1.9rem' }}>Security Workflow Dashboard</h1>
          <p style={{ color: '#475569', marginTop: 6 }}>Track scan runs, findings, and seed a sample Solidity contract.</p>
        </div>
        <button onClick={() => { loadProjects(); loadScans(); if (selectedScanId) loadScanDetail(selectedScanId) }} style={{ padding: '0.6rem 1rem', borderRadius: 10, border: '1px solid #cbd5e1', background: '#0ea5e9', color: '#fff', cursor: 'pointer' }}>
          Refresh data
        </button>
      </header>

      {toast && (
        <div
          style={{
            marginBottom: '1rem',
            padding: '0.75rem 1rem',
            borderRadius: 12,
            border: '1px solid',
            borderColor: toast.tone === 'error' ? '#fecdd3' : toast.tone === 'success' ? '#bbf7d0' : '#bfdbfe',
            background: toast.tone === 'error' ? '#fff1f2' : toast.tone === 'success' ? '#f0fdf4' : '#eff6ff',
            color: '#0f172a',
          }}
        >
          {toast.message}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1.1fr 0.9fr', gap: '1rem', alignItems: 'start' }}>
        <section style={sectionStyle}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <h2 style={{ margin: 0 }}>Projects</h2>
            {loadingProjects && <span style={{ color: '#94a3b8', fontSize: 12 }}>Loading…</span>}
          </div>
          {projects.length === 0 ? (
            <p style={{ color: '#475569' }}>No projects yet. Add one below to start scanning.</p>
          ) : (
            <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'grid', gap: '0.6rem' }}>
              {projects.map((p) => (
                <li key={p.id} style={{ background: '#f8fafc', padding: '0.75rem', borderRadius: 10, border: '1px solid #e2e8f0' }}>
                  <div style={{ fontWeight: 600 }}>{p.name}</div>
                  <div style={{ color: '#475569', fontSize: 14 }}>{p.path}</div>
                  {p.meta && <div style={{ color: '#94a3b8', fontSize: 12 }}>Meta: {JSON.stringify(p.meta)}</div>}
                </li>
              ))}
            </ul>
          )}

          <form onSubmit={handleCreateProject} style={{ marginTop: '1rem', display: 'grid', gap: '0.75rem' }}>
            <div style={{ display: 'grid', gap: 6 }}>
              <label style={{ fontWeight: 600 }}>Project name</label>
              <input
                required
                value={projectForm.name}
                onChange={(e) => setProjectForm((prev) => ({ ...prev, name: e.target.value }))}
                placeholder="ex: sample-audits"
                style={{ padding: '0.55rem 0.75rem', borderRadius: 8, border: '1px solid #cbd5e1' }}
              />
            </div>
            <div style={{ display: 'grid', gap: 6 }}>
              <label style={{ fontWeight: 600 }}>Path to contracts (used as scan target root)</label>
              <input
                required
                value={projectForm.path}
                onChange={(e) => setProjectForm((prev) => ({ ...prev, path: e.target.value }))}
                placeholder="/workspace/contracts"
                style={{ padding: '0.55rem 0.75rem', borderRadius: 8, border: '1px solid #cbd5e1' }}
              />
            </div>
            <div style={{ display: 'grid', gap: 6 }}>
              <label style={{ fontWeight: 600 }}>Meta (JSON optional)</label>
              <textarea
                value={projectForm.meta}
                onChange={(e) => setProjectForm((prev) => ({ ...prev, meta: e.target.value }))}
                placeholder='{"network": "sepolia"}'
                rows={2}
                style={{ padding: '0.55rem 0.75rem', borderRadius: 8, border: '1px solid #cbd5e1', resize: 'vertical' }}
              />
            </div>
            <button type="submit" style={{ padding: '0.7rem 1rem', background: '#22c55e', color: '#fff', border: 'none', borderRadius: 10, cursor: 'pointer' }}>
              Add project
            </button>
          </form>
        </section>

        <section style={sectionStyle}>
          <h2 style={{ marginTop: 0 }}>Start a scan</h2>
          <p style={{ color: '#475569', marginTop: 4 }}>Pick a project, choose tools, and provide a target path. Status updates every few seconds once started.</p>
          <form onSubmit={handleStartScan} style={{ display: 'grid', gap: '0.75rem' }}>
            <div style={{ display: 'grid', gap: 6 }}>
              <label style={{ fontWeight: 600 }}>Project</label>
              <select
                required
                value={scanForm.project_id}
                onChange={(e) => setScanForm((prev) => ({ ...prev, project_id: e.target.value }))}
                style={{ padding: '0.6rem 0.75rem', borderRadius: 10, border: '1px solid #cbd5e1' }}
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
            <div style={{ display: 'grid', gap: 6 }}>
              <label style={{ fontWeight: 600 }}>Target (file or directory)</label>
              <input
                required
                value={scanForm.target}
                onChange={(e) => setScanForm((prev) => ({ ...prev, target: e.target.value }))}
                placeholder="contracts/SampleToken.sol"
                style={{ padding: '0.6rem 0.75rem', borderRadius: 10, border: '1px solid #cbd5e1' }}
              />
            </div>
            <div style={{ display: 'grid', gap: 8 }}>
              <label style={{ fontWeight: 600 }}>Tools</label>
              <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                {TOOLBOX.map((tool) => {
                  const checked = scanForm.tools.includes(tool)
                  return (
                    <label key={tool} style={{ display: 'flex', alignItems: 'center', gap: 6, background: '#f1f5f9', padding: '0.4rem 0.6rem', borderRadius: 8, border: '1px solid #e2e8f0' }}>
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={(e) => {
                          const updated = e.target.checked
                            ? [...scanForm.tools, tool]
                            : scanForm.tools.filter((t) => t !== tool)
                          setScanForm((prev) => ({ ...prev, tools: updated }))
                        }}
                      />
                      {tool}
                    </label>
                  )
                })}
              </div>
            </div>
            <button type="submit" style={{ padding: '0.7rem 1rem', background: '#0ea5e9', color: '#fff', border: 'none', borderRadius: 10, cursor: 'pointer' }} disabled={!scanForm.project_id}>
              Start scan
            </button>
          </form>

          <div style={{ marginTop: '1.5rem', padding: '0.8rem', background: '#ecfeff', border: '1px solid #bae6fd', borderRadius: 10 }}>
            <div style={{ fontWeight: 700, marginBottom: 6 }}>Sample Solidity contract</div>
            <p style={{ color: '#0f172a', marginBottom: 10 }}>
              Use this starter file to validate the workflow. Download or copy it, place it under your project path (e.g. <code>contracts/SampleToken.sol</code>), then run a scan against that path.
            </p>
            <div style={{ display: 'flex', gap: 10 }}>
              <button onClick={handleCopySample} style={{ padding: '0.55rem 0.8rem', borderRadius: 10, border: '1px solid #38bdf8', background: '#fff', cursor: 'pointer' }}>
                Copy contract
              </button>
              <button onClick={handleDownloadSample} style={{ padding: '0.55rem 0.8rem', borderRadius: 10, border: '1px solid #38bdf8', background: '#0ea5e9', color: '#fff', cursor: 'pointer' }}>
                Download SampleToken.sol
              </button>
            </div>
          </div>
        </section>
      </div>

      <section style={{ ...sectionStyle, marginTop: '1rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h2 style={{ margin: 0 }}>Scan history</h2>
            <p style={{ color: '#475569', marginTop: 4 }}>Select a run to view live findings and logs.</p>
          </div>
          {loadingScans && <span style={{ color: '#94a3b8', fontSize: 12 }}>Updating…</span>}
        </div>
        <div style={{ overflowX: 'auto', marginTop: '0.75rem' }}>
          <table style={{ width: '100%', borderCollapse: 'separate', borderSpacing: 0 }}>
            <thead>
              <tr style={{ textAlign: 'left', color: '#475569' }}>
                <th style={{ padding: '0.5rem' }}>Status</th>
                <th style={{ padding: '0.5rem' }}>Project</th>
                <th style={{ padding: '0.5rem' }}>Target</th>
                <th style={{ padding: '0.5rem' }}>Tools</th>
                <th style={{ padding: '0.5rem' }}>Started</th>
                <th style={{ padding: '0.5rem' }}>Finished</th>
              </tr>
            </thead>
            <tbody>
              {scans.length === 0 && (
                <tr>
                  <td colSpan={6} style={{ padding: '0.8rem', color: '#475569' }}>
                    No scans yet. Kick off a scan to see live feedback.
                  </td>
                </tr>
              )}
              {scans.map((scan) => (
                <tr
                  key={scan.id}
                  onClick={() => setSelectedScanId(scan.id)}
                  style={{
                    background: selectedScanId === scan.id ? '#eef2ff' : '#fff',
                    cursor: 'pointer',
                    borderBottom: '1px solid #e2e8f0',
                  }}
                >
                  <td style={{ padding: '0.65rem' }}>
                    <span
                      style={{
                        background: badgeColor(scan.status),
                        padding: '0.25rem 0.5rem',
                        borderRadius: 999,
                        fontWeight: 700,
                        fontSize: 12,
                        border: '1px solid #e5e7eb',
                      }}
                    >
                      {scan.status}
                    </span>
                  </td>
                  <td style={{ padding: '0.65rem' }}>{scan.project_id}</td>
                  <td style={{ padding: '0.65rem' }}>{scan.target}</td>
                  <td style={{ padding: '0.65rem' }}>{scan.tools.join(', ')}</td>
                  <td style={{ padding: '0.65rem' }}>{new Date(scan.started_at).toLocaleString()}</td>
                  <td style={{ padding: '0.65rem' }}>{scan.finished_at ? new Date(scan.finished_at).toLocaleString() : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {selectedScanId && (
        <section style={sectionStyle}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <h2 style={{ margin: 0 }}>Findings for scan {selectedScanId}</h2>
              <p style={{ color: '#475569', marginTop: 4 }}>
                Severity and tool filters are available below. {loadingFindings && 'Refreshing findings…'}
              </p>
            </div>
            <button
              onClick={() => loadScanDetail(selectedScanId)}
              style={{ padding: '0.55rem 0.8rem', borderRadius: 10, border: '1px solid #cbd5e1', background: '#fff', cursor: 'pointer' }}
            >
              Reload findings
            </button>
          </div>
          <FindingsTable findings={selectedFindings} />

          {scanDetail?.logs && (
            <div style={{ marginTop: '1rem' }}>
              <h3 style={{ marginBottom: 6 }}>Worker feedback</h3>
              <pre
                style={{
                  background: '#0f172a',
                  color: '#e2e8f0',
                  padding: '0.9rem',
                  borderRadius: 10,
                  overflowX: 'auto',
                  maxHeight: 260,
                }}
              >
                {scanDetail.logs}
              </pre>
            </div>
          )}
        </section>
      )}
    </div>
  )
}

export default App
