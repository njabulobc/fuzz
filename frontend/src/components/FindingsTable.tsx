import React, { useMemo, useState } from 'react'

type Props = {
  findings: {
    id: string
    tool: string
    title: string
    description: string
    severity: string
    category?: string
    file_path?: string
    line_number?: string
  }[]
}

const severities = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO']

export const FindingsTable: React.FC<Props> = ({ findings }) => {
  const [severity, setSeverity] = useState<string>('')
  const [tool, setTool] = useState<string>('')

  const filtered = useMemo(() => {
    return findings.filter((f) => {
      return (!severity || f.severity === severity) && (!tool || f.tool === tool)
    })
  }, [findings, severity, tool])

  return (
    <div>
      <div style={{ marginBottom: '1rem' }}>
        <label>Severity filter: </label>
        <select value={severity} onChange={(e) => setSeverity(e.target.value)}>
          <option value="">All</option>
          {severities.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <label style={{ marginLeft: '1rem' }}>Tool filter: </label>
        <input value={tool} onChange={(e) => setTool(e.target.value)} placeholder="slither" />
      </div>
      <table border={1} cellPadding={6} cellSpacing={0} style={{ width: '100%' }}>
        <thead>
          <tr>
            <th>Severity</th>
            <th>Tool</th>
            <th>Category</th>
            <th>Title</th>
            <th>Location</th>
          </tr>
        </thead>
        <tbody>
          {filtered.map((f) => (
            <tr key={f.id}>
              <td>{f.severity}</td>
              <td>{f.tool}</td>
              <td>{f.category}</td>
              <td>{f.title}</td>
              <td>{f.file_path}:{f.line_number}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}