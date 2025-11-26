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

  const uniqueTools = useMemo(() => Array.from(new Set(findings.map((f) => f.tool))), [findings])

  const filtered = useMemo(() => {
    return findings.filter((f) => {
      return (!severity || f.severity === severity) && (!tool || f.tool === tool)
    })
  }, [findings, severity, tool])

  return (
    <div>
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: '0.75rem',
          alignItems: 'center',
          marginBottom: '1rem',
        }}
      >
        <div style={{ display: 'grid', gap: 6 }}>
          <label style={{ fontWeight: 600, color: '#0f172a' }}>Severity filter</label>
          <select
            value={severity}
            onChange={(e) => setSeverity(e.target.value)}
            style={{ padding: '0.45rem 0.6rem', borderRadius: 8, border: '1px solid #cbd5e1' }}
          >
            <option value="">All severities</option>
            {severities.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>

        <div style={{ display: 'grid', gap: 6 }}>
          <label style={{ fontWeight: 600, color: '#0f172a' }}>Tool filter</label>
          <select
            value={tool}
            onChange={(e) => setTool(e.target.value)}
            style={{ padding: '0.45rem 0.6rem', borderRadius: 8, border: '1px solid #cbd5e1' }}
          >
            <option value="">All tools</option>
            {uniqueTools.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </div>

        <button
          type="button"
          onClick={() => {
            setTool('')
            setSeverity('')
          }}
          style={{ padding: '0.55rem 0.9rem', borderRadius: 10, border: '1px solid #cbd5e1', background: '#fff', cursor: 'pointer' }}
        >
          Clear filters
        </button>
      </div>

      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'separate', borderSpacing: 0 }}>
          <thead>
            <tr style={{ textAlign: 'left', color: '#475569' }}>
              <th style={{ padding: '0.55rem' }}>Severity</th>
              <th style={{ padding: '0.55rem' }}>Tool</th>
              <th style={{ padding: '0.55rem' }}>Category</th>
              <th style={{ padding: '0.55rem' }}>Title</th>
              <th style={{ padding: '0.55rem' }}>Location</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 && (
              <tr>
                <td colSpan={5} style={{ padding: '0.9rem', color: '#475569' }}>
                  No findings match the selected filters yet.
                </td>
              </tr>
            )}
            {filtered.map((f) => (
              <tr key={f.id} style={{ background: '#fff', borderBottom: '1px solid #e2e8f0' }}>
                <td style={{ padding: '0.6rem' }}>
                  <span
                    style={{
                      background: '#f1f5f9',
                      borderRadius: 999,
                      padding: '0.2rem 0.55rem',
                      fontWeight: 700,
                      border: '1px solid #e2e8f0',
                    }}
                  >
                    {f.severity}
                  </span>
                </td>
                <td style={{ padding: '0.6rem' }}>{f.tool}</td>
                <td style={{ padding: '0.6rem' }}>{f.category ?? '—'}</td>
                <td style={{ padding: '0.6rem' }}>{f.title}</td>
                <td style={{ padding: '0.6rem', color: '#0f172a' }}>
                  {f.file_path ? `${f.file_path}:${f.line_number ?? '?'}` : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}