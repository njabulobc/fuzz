import React, { useEffect, useState } from 'react'
import axios from 'axios'
import { FindingsTable } from '../components/FindingsTable'

const API_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000/api'

type Project = { id: string; name: string; path: string }
type ToolOutcome = {
  tool: string
  success: boolean
  attempts: number
  duration_seconds?: number
  error?: string
  output?: string
  artifacts?: string[]
}
type Scan = {
  id: string
  project_id: string
  status: string
  target: string
  tools: string[]
  started_at: string
  tool_results?: ToolOutcome[]
}

type ContractGenerationResponse = {
  contract_name: string
  contract_path: string
  project: Project
  scan: Scan
}

type CrashReport = { id: string; signature: string; reproduction_status: string; log?: string }

type ScanDetail = Scan & {
  findings: Finding[]
  tool_results: ToolOutcome[]
  crash_reports: CrashReport[]
  telemetry?: Record<string, unknown>
  artifacts?: Record<string, string>
}

type Finding = {
  id: string
  tool: string
  title: string
  description: string
  severity: string
  category?: string
  file_path?: string
  line_number?: string
}

const App: React.FC = () => {
  const [projects, setProjects] = useState<Project[]>([])
  const [scans, setScans] = useState<Scan[]>([])
  const [selectedScan, setSelectedScan] = useState<string>('')
  const [selectedScanDetail, setSelectedScanDetail] = useState<ScanDetail | null>(null)
  const [findings, setFindings] = useState<Finding[]>([])
  const [generationMessage, setGenerationMessage] = useState<string>('')
  const [generationStatus, setGenerationStatus] = useState<'idle' | 'success' | 'error'>('idle')
  const [isGenerating, setIsGenerating] = useState<boolean>(false)

  useEffect(() => {
    axios.get(`${API_URL}/projects`).then((res) => setProjects(res.data))
    axios.get(`${API_URL}/scans`).then((res) => setScans(res.data))
  }, [])

  useEffect(() => {
    if (selectedScan) {
      axios.get(`${API_URL}/scans/${selectedScan}`).then((res) => {
        setFindings(res.data.findings)
        setSelectedScanDetail(res.data)
      })
    }
  }, [selectedScan])

  const handleGenerateContract = async () => {
    setIsGenerating(true)
    setGenerationMessage('')
    setGenerationStatus('idle')
    try {
      const res = await axios.post<ContractGenerationResponse>(`${API_URL}/contracts/generate-and-scan`)
      const data = res.data
      setProjects((prev) => [data.project, ...prev])
      setScans((prev) => [data.scan, ...prev])
      setSelectedScan(data.scan.id)
      setGenerationStatus('success')
      setGenerationMessage(
        `Generated ${data.contract_name} at ${data.contract_path} and queued a fuzz scan automatically.`
      )
    } catch (err) {
      setGenerationStatus('error')
      setGenerationMessage('We could not generate a sample contract. Check backend logs for details.')
    } finally {
      setIsGenerating(false)
    }
  }

  return (
    <div style={{ padding: '2rem', fontFamily: 'sans-serif' }}>
      <h1>Smart Contract Scan Dashboard</h1>
      <section
        style={{
          marginBottom: '1.5rem',
          padding: '1.5rem',
          border: '1px solid #d6e2ff',
          borderRadius: 12,
          background: '#f5f8ff',
        }}
      >
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1.25rem', alignItems: 'flex-start' }}>
          <div style={{ flex: '2 1 320px' }}>
            <p style={{ margin: 0, fontWeight: 600, color: '#2d3a8c', letterSpacing: 0.2 }}>
              One-click smart contract fuzzing
            </p>
            <h2 style={{ margin: '0.25rem 0 0.5rem 0' }}>Generate a sample contract and run a scan</h2>
            <p style={{ marginTop: 0, color: '#3a416f', lineHeight: 1.5 }}>
              Use this quick start to go from nothing to a running fuzz job. We create a themed Solidity
              contract for you, register it as a project, and queue a scan automatically so results appear
              below.
            </p>
            <ol style={{ marginTop: 0, paddingLeft: '1.25rem', color: '#3a416f', lineHeight: 1.5 }}>
              <li>Click the button — no inputs required.</li>
              <li>We write the contract to disk and register it as a new project.</li>
              <li>Watch the Projects and Scans tables update; click the newest scan to inspect details.</li>
            </ol>
            <button
              onClick={handleGenerateContract}
              disabled={isGenerating}
              style={{
                padding: '0.75rem 1.25rem',
                fontSize: '1rem',
                fontWeight: 700,
                background: isGenerating ? '#7e93d8' : '#2d3a8c',
                color: 'white',
                border: 'none',
                borderRadius: 8,
                cursor: isGenerating ? 'progress' : 'pointer',
              }}
            >
              {isGenerating ? 'Generating & starting fuzz scan…' : 'Generate contract and start fuzzing'}
            </button>
          </div>
          <div
            style={{
              flex: '1 1 260px',
              background: 'white',
              border: '1px solid #e4e9ff',
              borderRadius: 12,
              padding: '1rem',
              boxShadow: '0 4px 12px rgba(45,58,140,0.08)',
            }}
          >
            <p style={{ marginTop: 0, fontWeight: 700, color: '#2d3a8c' }}>What happens next?</p>
            <ul style={{ margin: 0, paddingLeft: '1.1rem', color: '#3a416f', lineHeight: 1.5 }}>
              <li>The new project appears at the top of the Projects list.</li>
              <li>A new scan is added with status updates in real time.</li>
              <li>Select the latest scan row to view tool outcomes, crashes, and artifacts.</li>
            </ul>
            {generationMessage && (
              <div
                style={{
                  marginTop: '0.85rem',
                  padding: '0.75rem',
                  borderRadius: 8,
                  background: generationStatus === 'error' ? '#fff5f5' : '#f0f8f0',
                  color: generationStatus === 'error' ? '#a23434' : '#1a4',
                  border: `1px solid ${generationStatus === 'error' ? '#f2c7c7' : '#b8e6c0'}`,
                }}
                aria-live="polite"
              >
                {generationMessage}
              </div>
            )}
          </div>
        </div>
      </section>
      <section>
        <h2>Projects</h2>
        <ul>
          {projects.map((p) => (
            <li key={p.id}>{p.name} - {p.path}</li>
          ))}
        </ul>
      </section>

      <section>
        <h2>Scans</h2>
        <table border={1} cellPadding={6} cellSpacing={0}>
          <thead>
            <tr>
              <th>ID</th>
              <th>Status</th>
              <th>Project</th>
              <th>Target</th>
              <th>Tools</th>
              <th>Started</th>
            </tr>
          </thead>
          <tbody>
            {scans.map((s) => (
                <tr
                key={s.id}
                onClick={() => {
                  setSelectedScan(s.id)
                  setSelectedScanDetail(null)
                  setFindings([])
                }}
                style={{ cursor: 'pointer', background: selectedScan === s.id ? '#eef' : 'white' }}
              >
                <td>{s.id}</td>
                <td>{s.status}</td>
                <td>{s.project_id}</td>
                <td>{s.target}</td>
                <td>{s.tools.join(', ')}</td>
                <td>{new Date(s.started_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {selectedScanDetail && (
        <section>
          <h2>Tool outcomes</h2>
          <table border={1} cellPadding={6} cellSpacing={0} width="100%">
            <thead>
              <tr>
                <th>Tool</th>
                <th>Status</th>
                <th>Attempts</th>
                <th>Duration (s)</th>
                <th>Errors</th>
              </tr>
            </thead>
            <tbody>
              {selectedScanDetail.tool_results?.map((r) => (
                <tr key={`${selectedScanDetail.id}-${r.tool}`}>
                  <td>{r.tool}</td>
                  <td style={{ color: r.success ? 'green' : 'red' }}>{r.success ? 'SUCCESS' : 'FAILED'}</td>
                  <td>{r.attempts}</td>
                  <td>{r.duration_seconds?.toFixed(2) ?? 'n/a'}</td>
                  <td style={{ maxWidth: 320 }}>{r.error ?? ''}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {selectedScanDetail && selectedScanDetail.crash_reports.length > 0 && (
        <section>
          <h2>Crash triage</h2>
          <ul>
            {selectedScanDetail.crash_reports.map((crash) => (
              <li key={crash.id}>
                <strong>{crash.signature}</strong> — {crash.reproduction_status}
                {crash.log ? <pre style={{ whiteSpace: 'pre-wrap' }}>{crash.log}</pre> : null}
              </li>
            ))}
          </ul>
        </section>
      )}

      {selectedScanDetail && (
        <section>
          <h2>Telemetry & artifacts</h2>
          <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
            <div style={{ flex: 1 }}>
              <h3>Telemetry snapshot</h3>
              <pre style={{ background: '#f7f7f7', padding: '0.5rem', maxHeight: 200, overflow: 'auto' }}>
                {JSON.stringify(selectedScanDetail.telemetry ?? {}, null, 2)}
              </pre>
            </div>
            <div style={{ flex: 1 }}>
              <h3>Artifacts</h3>
              <pre style={{ background: '#f7f7f7', padding: '0.5rem', maxHeight: 200, overflow: 'auto' }}>
                {JSON.stringify(selectedScanDetail.artifacts ?? {}, null, 2)}
              </pre>
            </div>
          </div>
          <p>
            Reports: <a href={`${API_URL}/reports/${selectedScanDetail.id}/sarif`} target="_blank">SARIF</a> |{' '}
            <a href={`${API_URL}/reports/${selectedScanDetail.id}/json`} target="_blank">JSON</a>
          </p>
        </section>
      )}

      {selectedScan && (
        <section>
          <h2>Findings</h2>
          <FindingsTable findings={findings} />
        </section>
      )}
    </div>
  )
}

export default App
