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
    try {
      const res = await axios.post<ContractGenerationResponse>(`${API_URL}/contracts/generate-and-scan`)
      const data = res.data
      setProjects((prev) => [data.project, ...prev])
      setScans((prev) => [data.scan, ...prev])
      setSelectedScan(data.scan.id)
      setGenerationMessage(
        `Generated ${data.contract_name} at ${data.contract_path} and queued a fuzz scan automatically.`
      )
    } catch (err) {
      setGenerationMessage('Failed to generate contract. See backend logs for details.')
    } finally {
      setIsGenerating(false)
    }
  }

  return (
    <div style={{ padding: '2rem', fontFamily: 'sans-serif' }}>
      <h1>Smart Contract Scan Dashboard</h1>
      <section style={{ marginBottom: '1rem' }}>
        <button onClick={handleGenerateContract} disabled={isGenerating}>
          {isGenerating ? 'Generating & starting fuzz scan...' : 'Generate contract + fuzz it'}
        </button>
        {generationMessage && <p style={{ marginTop: '0.5rem' }}>{generationMessage}</p>}
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
