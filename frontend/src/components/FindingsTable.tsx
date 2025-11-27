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

export const FindingsTable: React.FC<Props> = ({ findings }) => {
  const [severity, setSeverity] = useState<string>('')
  const [tool, setTool] = useState<string>('')
  const [expandedId, setExpandedId] = useState<string>('')

  const severitySummary = useMemo(() => {
    return findings.reduce<Record<string, number>>((acc, finding) => {
      acc[finding.severity] = (acc[finding.severity] ?? 0) + 1
      return acc
    }, {})
  }, [findings])

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

  const explainFinding = (finding: Props['findings'][number]): string => {
    const severityImpact: Record<string, string> = {
      CRITICAL: 'needs immediate attention because it can be exploited to drain funds or seize control.',
      HIGH: 'is high impact and could be exploited in realistic conditions.',
      MEDIUM: 'has moderate impact. It may need specific conditions but still affects reliability or trust.',
      LOW: 'is low impact. It can erode confidence or create maintenance risk.',
      INFO: 'is informational. It highlights hygiene issues or potential improvements.',
    }

    const categoryTips: Record<string, string> = {
      reentrancy: 'reentrancy issues can let attackers call back into contracts and bypass balance updates.',
      authorization: 'missing or weak authorization checks can let attackers trigger privileged functions.',
      arithmetic: 'unchecked arithmetic can overflow/underflow and corrupt balances or limits.',
      validation: 'input validation gaps can accept unsafe parameters or stale data.',
      gas: 'gas usage concerns can make functions unusable in production due to high costs.',
    }

    const parts: string[] = []
    if (finding.description) {
      parts.push(`The tool reported: ${finding.description}`)
    }

    const categoryKey = (finding.category || '').toLowerCase()
    if (categoryKey && categoryTips[categoryKey]) {
      parts.push(categoryTips[categoryKey])
    }

    if (finding.severity && severityImpact[finding.severity]) {
      parts.push(`Severity ${finding.severity} ${severityImpact[finding.severity]}`)
    }

    if (finding.file_path) {
      const location = finding.line_number ? `${finding.file_path}:${finding.line_number}` : finding.file_path
      parts.push(`Flagged near ${location}${finding.function ? ` in ${finding.function}()` : ''}.`)
    }

    return parts.join(' ')
  }

  return (
    <div className="mt-4">
      <div className="flex flex-wrap gap-2">
        {severities.map((s) => (
          <span
            key={s}
            className={`inline-flex items-center gap-1 rounded-full border px-3 py-1 text-[11px] font-semibold ${
              severityColors[s]
            }`}
          >
            {s}
            <span className="rounded-full bg-white px-2 py-0.5 text-[10px] font-bold text-slate-700">
              {severitySummary[s] ?? 0}
            </span>
          </span>
        ))}
      </div>

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
              <th className="px-3 py-2">Title</th>
              <th className="px-3 py-2">Location</th>
              <th className="px-3 py-2 text-right">Explain</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {filtered.map((f) => {
              const isExpanded = expandedId === f.id
              return (
                <React.Fragment key={f.id}>
                  <tr className="bg-white hover:bg-slate-50">
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
                      <div className="text-xs text-slate-600">{f.description}</div>
                    </td>
                    <td className="px-3 py-3 text-slate-600">
                      {f.file_path ?? 'unknown'}
                      {f.line_number ? `:${f.line_number}` : ''}
                    </td>
                    <td className="px-3 py-3 text-right">
                      <button
                        type="button"
                        onClick={() => setExpandedId(isExpanded ? '' : f.id)}
                        className="text-xs font-semibold text-sky-700 hover:text-sky-900"
                      >
                        {isExpanded ? 'Hide' : 'Explain'}
                      </button>
                    </td>
                  </tr>
                  {isExpanded && (
                    <tr className="bg-slate-50">
                      <td colSpan={6} className="px-4 py-3 text-sm text-slate-800">
                        <div className="space-y-2">
                          <p>
                            <span className="font-semibold text-slate-900">What the tool reported: </span>
                            {f.description}
                          </p>
                          <p>
                            <span className="font-semibold text-slate-900">Why this matters: </span>
                            {explainFinding(f)}
                          </p>
                          {f.function && (
                            <p className="text-xs text-slate-600">Function context: {f.function}</p>
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}