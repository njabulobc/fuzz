import React, { useEffect, useState } from 'react'
import axios from 'axios'
import { FindingsTable } from '../components/FindingsTable'

const API_URL = 'http://localhost:8000/api'

type Project = { id: string; name: string; path: string }
type ToolRun = {
  id: string
  tool: string
  status: string
  attempts: number
  exit_code?: number
  output?: string
  error?: string
  metrics?: Record<string, unknown>
}
type Scan = {
  id: string
  project_id: string
  status: string
  target: string
  tools: string[]
  started_at: string
  finished_at?: string
}

type ScanDetail = Scan & {
  findings: Finding[]
  tool_runs: ToolRun[]
  telemetry?: Record<string, unknown>
  artifacts?: Record<string, unknown>[]
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

type Campaign = {
  id: string
  name: string
  target: string
  status: string
  strategy?: string
  coverage?: Record<string, unknown>
  metrics?: Record<string, unknown>
}

type CampaignDetail = Campaign & {
  seeds: { id: string; source: string }[]
  crashes: Crash[]
  signals: { id: string; run_identifier?: string; covered_edges: number }[]
}

type Crash = {
  id: string
  signature: string
  status: string
  input_reference?: string
  stacktrace?: string
}

const App: React.FC = () => {
  const [projects, setProjects] = useState<Project[]>([])
  const [scans, setScans] = useState<Scan[]>([])
  const [selectedScan, setSelectedScan] = useState<string>('')
  const [scanDetail, setScanDetail] = useState<ScanDetail | null>(null)
  const [findings, setFindings] = useState<Finding[]>([])
  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [selectedCampaign, setSelectedCampaign] = useState<string>('')
  const [campaignDetail, setCampaignDetail] = useState<CampaignDetail | null>(null)

  useEffect(() => {
    axios.get(`${API_URL}/projects`).then((res) => setProjects(res.data))
    axios.get(`${API_URL}/scans`).then((res) => setScans(res.data))
    axios.get(`${API_URL}/campaigns`).then((res) => setCampaigns(res.data))
  }, [])

  useEffect(() => {
    if (selectedScan) {
      axios.get(`${API_URL}/scans/${selectedScan}`).then((res) => {
        setFindings(res.data.findings)
        setScanDetail(res.data)
      })
    }
  }, [selectedScan])

  useEffect(() => {
    if (selectedCampaign) {
      axios.get(`${API_URL}/campaigns/${selectedCampaign}`).then((res) => setCampaignDetail(res.data))
    }
  }, [selectedCampaign])

  return (
    <div style={{ padding: '2rem', fontFamily: 'sans-serif' }}>
      <h1>Smart Contract Scan Dashboard</h1>

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
        <table border={1} cellPadding={6} cellSpacing={0} style={{ width: '100%' }}>
          <thead>
            <tr>
              <th>ID</th>
              <th>Status</th>
              <th>Project</th>
              <th>Target</th>
              <th>Tools</th>
              <th>Started</th>
              <th>Finished</th>
            </tr>
          </thead>
          <tbody>
            {scans.map((s) => (
              <tr key={s.id} onClick={() => setSelectedScan(s.id)} style={{ cursor: 'pointer', background: selectedScan === s.id ? '#eef' : 'white' }}>
                <td>{s.id}</td>
                <td>{s.status}</td>
                <td>{s.project_id}</td>
                <td>{s.target}</td>
                <td>{s.tools.join(', ')}</td>
                <td>{new Date(s.started_at).toLocaleString()}</td>
                <td>{s.finished_at ? new Date(s.finished_at).toLocaleString() : '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {selectedScan && (
          <div style={{ marginTop: '1rem' }}>
            <a href={`${API_URL}/scans/${selectedScan}/sarif`} target="_blank" rel="noreferrer">SARIF export</a>
            <span style={{ marginLeft: '1rem' }}>
              <a href={`${API_URL}/scans/${selectedScan}/report`} target="_blank" rel="noreferrer">JSON export</a>
            </span>
          </div>
        )}
      </section>

      {scanDetail && (
        <section style={{ marginTop: '2rem' }}>
          <h2>Tool Runs</h2>
          <table border={1} cellPadding={6} cellSpacing={0} style={{ width: '100%' }}>
            <thead>
              <tr>
                <th>Tool</th>
                <th>Status</th>
                <th>Attempts</th>
                <th>Exit</th>
                <th>Runtime</th>
                <th>Stdout</th>
                <th>Stderr</th>
              </tr>
            </thead>
            <tbody>
              {scanDetail.tool_runs.map((tr) => (
                <tr key={tr.id}>
                  <td>{tr.tool}</td>
                  <td>{tr.status}</td>
                  <td>{tr.attempts}</td>
                  <td>{tr.exit_code ?? '-'}</td>
                  <td>{(tr.metrics as any)?.runtime_seconds ?? '-'}</td>
                  <td><pre style={{ whiteSpace: 'pre-wrap', maxWidth: 300 }}>{tr.output?.slice(0, 200)}</pre></td>
                  <td><pre style={{ whiteSpace: 'pre-wrap', maxWidth: 300 }}>{tr.error?.slice(0, 200)}</pre></td>
                </tr>
              ))}
            </tbody>
          </table>
          <h3>Scan Telemetry</h3>
          <pre style={{ background: '#f8f8f8', padding: '1rem' }}>{JSON.stringify(scanDetail.telemetry, null, 2)}</pre>
          <h3>Artifacts</h3>
          <pre style={{ background: '#f8f8f8', padding: '1rem' }}>{JSON.stringify(scanDetail.artifacts, null, 2)}</pre>
        </section>
      )}

      {selectedScan && (
        <section style={{ marginTop: '2rem' }}>
          <h2>Findings</h2>
          <FindingsTable findings={findings} />
        </section>
      )}

      <section style={{ marginTop: '2rem' }}>
        <h2>Fuzzing Campaigns</h2>
        <table border={1} cellPadding={6} cellSpacing={0} style={{ width: '100%' }}>
          <thead>
            <tr>
              <th>Name</th>
              <th>Status</th>
              <th>Target</th>
              <th>Strategy</th>
              <th>Coverage</th>
              <th>Crashes</th>
            </tr>
          </thead>
          <tbody>
            {campaigns.map((c) => (
              <tr key={c.id} onClick={() => setSelectedCampaign(c.id)} style={{ cursor: 'pointer', background: selectedCampaign === c.id ? '#eef' : 'white' }}>
                <td>{c.name}</td>
                <td>{c.status}</td>
                <td>{c.target}</td>
                <td>{c.strategy || '-'}</td>
                <td>{(c.coverage as any)?.covered_edges ?? '-'}</td>
                <td>{(c.metrics as any)?.crashes ?? 0}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {campaignDetail && (
        <section style={{ marginTop: '1rem' }}>
          <h3>Crash Triage</h3>
          <table border={1} cellPadding={6} cellSpacing={0} style={{ width: '100%' }}>
            <thead>
              <tr>
                <th>Signature</th>
                <th>Status</th>
                <th>Input</th>
                <th>Stacktrace</th>
              </tr>
            </thead>
            <tbody>
              {campaignDetail.crashes.map((crash) => (
                <tr key={crash.id}>
                  <td>{crash.signature}</td>
                  <td>{crash.status}</td>
                  <td>{crash.input_reference || '-'}</td>
                  <td><pre style={{ whiteSpace: 'pre-wrap', maxWidth: 400 }}>{crash.stacktrace || ''}</pre></td>
                </tr>
              ))}
            </tbody>
          </table>
          <h3>Coverage Signals</h3>
          <ul>
            {campaignDetail.signals.map((sig) => (
              <li key={sig.id}>Run {sig.run_identifier || '-'}: {sig.covered_edges} edges</li>
            ))}
          </ul>
        </section>
      )}
    </div>
  )
}

export default App
