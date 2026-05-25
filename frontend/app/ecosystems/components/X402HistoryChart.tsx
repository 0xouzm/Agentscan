'use client'

import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import type { X402HistoryPoint } from '@/types'

function formatCompact(value: number | null | undefined, prefix = ''): string {
  if (value == null || Number.isNaN(value)) return '--'
  const abs = Math.abs(value)
  const sign = value < 0 ? '-' : ''
  if (abs >= 1e9) return `${sign}${prefix}${(abs / 1e9).toFixed(2)}B`
  if (abs >= 1e6) return `${sign}${prefix}${(abs / 1e6).toFixed(2)}M`
  if (abs >= 1e3) return `${sign}${prefix}${(abs / 1e3).toFixed(2)}K`
  return `${sign}${prefix}${abs.toLocaleString(undefined, { maximumFractionDigits: 2 })}`
}

function formatTime(value: string): string {
  return new Date(value).toLocaleString(undefined, {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

type TrendKey = 'transactions_30d' | 'volume_30d' | 'total_resources' | 'x402_capability_agents'

function latestDelta(rows: X402HistoryPoint[], key: TrendKey): number | null {
  if (rows.length < 2) return null
  const current = rows[rows.length - 1][key]
  const previous = rows[rows.length - 2][key]
  if (typeof current !== 'number' || typeof previous !== 'number') return null
  return current - previous
}

function Delta({ value, prefix = '' }: { value: number | null; prefix?: string }) {
  if (value == null) return <span className="text-[#a3a3a3]">--</span>
  if (value === 0) return <span className="text-[#a3a3a3]">0</span>
  const positive = value > 0
  return (
    <span className={positive ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}>
      {positive ? '+' : '-'}{formatCompact(Math.abs(value), prefix)}
    </span>
  )
}

export default function X402HistoryChart({
  rows,
  loading,
}: {
  rows: X402HistoryPoint[]
  loading: boolean
}) {
  const latest = rows.at(-1)
  const data = rows.map((row) => ({
    ...row,
    label: formatTime(row.snapshot_time),
  }))

  return (
    <div className="mt-6 rounded-2xl border border-[#d6f5df] bg-white p-5 dark:border-[#143924] dark:bg-[#0d1b13]">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <h3 title="Historical snapshots saved by Agentscan from x402.org, Coinbase CDP Bazaar, and local Agentscan metadata." className="text-sm font-semibold text-[#0a0a0a] dark:text-[#fafafa]">
          x402 Key Metric History
        </h3>
        <div className="grid grid-cols-2 gap-3 text-right text-[12px] lg:grid-cols-4">
          <TrendStat label="30D Tx" value={latest?.transactions_30d} delta={latestDelta(rows, 'transactions_30d')} title="Official x402.org completed payments over the last 30 days." />
          <TrendStat label="30D Vol" value={latest?.volume_30d} delta={latestDelta(rows, 'volume_30d')} prefix="$" title="Official x402.org settlement volume over the last 30 days." />
          <TrendStat label="Bazaar" value={latest?.total_resources} delta={latestDelta(rows, 'total_resources')} title="Public paid HTTP resources reported by Coinbase CDP Bazaar discovery." />
          <TrendStat label="Agentscan" value={latest?.x402_capability_agents} delta={latestDelta(rows, 'x402_capability_agents')} title="Local Agentscan agents tagged with x402 capability." />
        </div>
      </div>
      <div className="mt-5 h-64">
        {loading && rows.length === 0 ? (
          <div className="h-full w-full animate-pulse rounded-xl bg-[#d6f5df] dark:bg-[#143924]" />
        ) : rows.length === 0 ? (
          <div className="flex h-full items-center justify-center text-[12px] text-[#737373]">
            History starts after the first successful x402 scan.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 10, right: 8, left: -24, bottom: 0 }}>
              <XAxis dataKey="label" tick={{ fontSize: 11, fill: '#737373' }} tickLine={false} axisLine={false} />
              <YAxis yAxisId="tx" tick={{ fontSize: 11, fill: '#737373' }} tickLine={false} axisLine={false} />
              <YAxis yAxisId="vol" orientation="right" tickFormatter={(value) => formatCompact(Number(value), '$')} tick={{ fontSize: 11, fill: '#737373' }} tickLine={false} axisLine={false} />
              <Tooltip
                formatter={(value, name) => [
                  name === '30D Volume' ? formatCompact(Number(value), '$') : formatCompact(Number(value)),
                  name,
                ]}
                contentStyle={{ borderRadius: 8, borderColor: '#b7e4c7', fontSize: 12 }}
              />
              <Line yAxisId="tx" name="30D Tx" type="monotone" dataKey="transactions_30d" stroke="#16a34a" strokeWidth={2.5} dot={{ r: 3 }} activeDot={{ r: 5 }} />
              <Line yAxisId="vol" name="30D Volume" type="monotone" dataKey="volume_30d" stroke="#2563eb" strokeWidth={2.5} dot={{ r: 3 }} activeDot={{ r: 5 }} />
              <Line yAxisId="tx" name="Bazaar Resources" type="monotone" dataKey="total_resources" stroke="#f59e0b" strokeWidth={2} dot={{ r: 3 }} activeDot={{ r: 5 }} />
              <Line yAxisId="tx" name="Agentscan x402 Tags" type="monotone" dataKey="x402_capability_agents" stroke="#7c3aed" strokeWidth={2} strokeDasharray="4 4" dot={{ r: 3 }} activeDot={{ r: 5 }} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  )
}

function TrendStat({
  label,
  value,
  delta,
  title,
  prefix = '',
}: {
  label: string
  value: number | null | undefined
  delta: number | null
  title: string
  prefix?: string
}) {
  return (
    <div title={title}>
      <div className="text-[10px] uppercase tracking-[0.14em] text-[#126b3a] dark:text-[#86efac]">{label}</div>
      <div className="mt-1 font-mono text-[#0a0a0a] dark:text-[#fafafa]">{formatCompact(value, prefix)}</div>
      <div className="text-[11px]"><Delta value={delta} prefix={prefix} /></div>
    </div>
  )
}
