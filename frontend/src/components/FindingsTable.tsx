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
    function?: string
  }[]
}

const severities = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO']

const severityGuidance: Record<string, string> = {
  CRITICAL: 'Critical issues frequently indicate exploits that put funds or ownership at direct risk.',
  HIGH: 'High severity items can block production deploys and warrant immediate review.',
  MEDIUM: 'Medium issues may be contextual—review and triage based on business impact.',
  LOW: 'Low severity findings are often hygiene improvements or informational signals.',
  INFO: 'Informational items provide additional context from the tool output.',
}

const buildExplanation = (finding: Props['findings'][number]) => {
  const location = [finding.file_path, finding.line_number].filter(Boolean).join(': ') || 'an unknown location'
  const category = finding.category ? `Category: ${finding.category}.` : ''
  const functionContext = finding.function ? `Observed near function ${finding.function}.` : ''
  const impact = severityGuidance[finding.severity] ?? 'Review the finding and the raw output for additional context.'

  return `${finding.tool} flagged a ${finding.severity.toLowerCase()} issue at ${location}. ${category} ${functionContext} ${impact}`
}

export const FindingsTable: React.FC<Props> = ({ findings }) => {
  const [severity, setSeverity] = useState<string>('')
  const [tool, setTool] = useState<string>('')

  const filtered = useMemo(() => {
    return findings.filter((f) => {
      return (!severity || f.severity === severity) && (!tool || f.tool === tool)
    })
  }, [findings, severity, tool])

  const severityColors: Record<string, string> = {
    CRITICAL: 'bg-rose-50 text-rose-700 border-rose-100',
    HIGH: 'bg-amber-50 text-amber-700 border-amber-100',
    MEDIUM: 'bg-yellow-50 text-yellow-700 border-yellow-100',
    LOW: 'bg-sky-50 text-sky-700 border-sky-100',
    INFO: 'bg-slate-100 text-slate-700 border-slate-200',
  }

  return (
    <div className="mt-4">
      <div className="flex flex-wrap items-center gap-4 rounded-lg border border-slate-200 bg-slate-50 px-3 py-3 text-sm">
        <label className="text-slate-700">
          Severity:
          <select
            value={severity}
            onChange={(e) => setSeverity(e.target.value)}
            className="ml-2 rounded-md border border-slate-200 bg-white px-2 py-1 text-xs font-medium text-slate-800 focus:border-sky-400 focus:outline-none focus:ring-2 focus:ring-sky-100"
          >
            <option value="">All</option>
            {severities.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        <label className="text-slate-700">
          Tool:
          <input
            value={tool}
            onChange={(e) => setTool(e.target.value)}
            placeholder="slither"
            className="ml-2 rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-800 focus:border-sky-400 focus:outline-none focus:ring-2 focus:ring-sky-100"
          />
        </label>
        <span className="rounded-full bg-white px-3 py-1 text-[11px] font-semibold text-slate-500">
          {filtered.length} finding{filtered.length === 1 ? '' : 's'}
        </span>
      </div>

      <div className="mt-3 overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-3 py-2">Severity</th>
              <th className="px-3 py-2">Tool</th>
              <th className="px-3 py-2">Category</th>
              <th className="px-3 py-2">Title & description</th>
              <th className="px-3 py-2">Why it matters</th>
              <th className="px-3 py-2">Location</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {filtered.map((f) => (
              <tr key={f.id} className="bg-white hover:bg-slate-50">
                <td className="px-3 py-3">
                  <span
                    className={`inline-flex rounded-full border px-3 py-1 text-[11px] font-bold uppercase ${
                      severityColors[f.severity] ?? 'bg-slate-100 text-slate-700 border-slate-200'
                    }`}
                  >
                    {f.severity}
                  </span>
                </td>
                <td className="px-3 py-3 font-semibold text-slate-800">{f.tool}</td>
                <td className="px-3 py-3 text-slate-700">{f.category ?? '—'}</td>
                <td className="px-3 py-3 text-slate-900">
                  <div className="font-semibold text-slate-900">{f.title}</div>
                  <p className="mt-1 text-sm text-slate-600">{f.description}</p>
                </td>
                <td className="px-3 py-3 text-slate-700">{buildExplanation(f)}</td>
                <td className="px-3 py-3 text-slate-600">
                  {f.file_path ?? 'unknown'}
                  {f.line_number ? `:${f.line_number}` : ''}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}