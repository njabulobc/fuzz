import React, { useEffect, useState } from 'react'
import axios from 'axios'
import { FindingsTable } from '../components/FindingsTable'

const API_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000/api'

type Project = { id: string; name: string; path: string }
type Scan = { id: string; project_id: string; status: string; target: string; tools: string[]; started_at: string }

type Finding = {
  id: string;
  tool: string;
  title: string;
  description: string;
  severity: string;
  category?: string;
  file_path?: string;
  line_number?: string;
}

const App: React.FC = () => {
  const [projects, setProjects] = useState<Project[]>([])
  const [scans, setScans] = useState<Scan[]>([])
  const [selectedScan, setSelectedScan] = useState<string>('')
  const [findings, setFindings] = useState<Finding[]>([])

  useEffect(() => {
    axios.get(`${API_URL}/projects`).then((res) => setProjects(res.data))
    axios.get(`${API_URL}/scans`).then((res) => setScans(res.data))
  }, [])

  useEffect(() => {
    if (selectedScan) {
      axios.get(`${API_URL}/scans/${selectedScan}`).then((res) => setFindings(res.data.findings))
    }
  }, [selectedScan])

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
                onClick={() => setSelectedScan(s.id)}
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