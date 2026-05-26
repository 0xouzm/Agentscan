'use client'

import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import type { X402Count, X402PriceBucket, X402Resource, X402ScanResponse } from '@/types'
import X402HistoryChart from './X402HistoryChart'

function formatInt(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return '--'
  return Math.round(value).toLocaleString()
}

function formatMoney(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return '--'
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(2)}M`
  if (value >= 1_000) return `$${(value / 1_000).toFixed(2)}K`
  return `$${value.toLocaleString(undefined, { maximumFractionDigits: 4 })}`
}

function shortNetwork(value: string): string {
  const map: Record<string, string> = {
    'eip155:8453': 'Base',
    'eip155:84532': 'Base Sepolia',
    'eip155:137': 'Polygon',
    'solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp': 'Solana',
    base: 'Base',
  }
  return map[value] ?? value.replace('eip155:', 'chain ')
}

const ROW_HINTS: Record<string, string> = {
  'Agentscan x402 agents': 'Local Agentscan agents whose metadata declares x402 capability.',
  'AgentKit tags': 'Local Agentscan agents whose metadata references Coinbase AgentKit.',
  'Payable agents': 'Local Agentscan agents whose metadata indicates a payable endpoint or payment capability.',
  'Discovery status': 'Whether the Coinbase CDP x402 Bazaar discovery API returned a usable live sample.',
  'x402 version': 'Protocol version value observed in sampled Bazaar discovery resources.',
}

export default function X402Section({
  scan,
  loading,
}: {
  scan: X402ScanResponse | null
  loading: boolean
}) {
  const stats = scan?.official_stats
  const discovery = scan?.discovery
  const agentscan = scan?.agentscan

  return (
    <section className="mt-8 rounded-[32px] border border-[#b7e4c7] bg-[#f8fff9] p-6 shadow-sm dark:border-[#174c32] dark:bg-[#08150f] sm:p-8">
      <div className="mb-8 flex flex-col gap-4 border-b border-[#d6f5df] pb-6 md:flex-row md:items-end md:justify-between dark:border-[#143924]">
        <div>
          <div className="mb-4 flex items-center gap-3">
            <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl bg-[#0a0a0a] text-[18px] font-bold tracking-tight text-white dark:bg-[#fafafa] dark:text-[#0a0a0a]">
              x402
            </div>
            <div className="flex flex-col">
              <span className="text-[15px] font-semibold leading-none text-[#0a0a0a] dark:text-[#fafafa]">
                x402
              </span>
              <span className="mt-1 text-[11px] font-medium uppercase tracking-[0.14em] text-[#126b3a] dark:text-[#86efac]">
                Machine payments
              </span>
            </div>
            <span className="rounded-full bg-[#16a34a] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-white">
              Live payments
            </span>
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-[#0a0a0a] dark:text-[#fafafa]">
            x402 + Coinbase CDP - Machine Payments
          </h2>
        </div>
        <div className="flex flex-wrap gap-2 text-[11px] font-medium">
          <ExternalButton href="https://www.x402.org">x402.org</ExternalButton>
          <ExternalButton href="https://docs.x402.org">Docs</ExternalButton>
          <ExternalButton href="https://github.com/x402-foundation/x402">GitHub</ExternalButton>
          <ExternalButton href="https://api.cdp.coinbase.com/platform/v2/x402/discovery/resources">Bazaar API</ExternalButton>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard label="30D Transactions" value={stats?.transactions?.display ?? '--'} hint="Official x402.org count of completed x402 payments over the last 30 days." loading={loading} />
        <MetricCard label="30D Volume" value={stats?.volume?.display ?? '--'} hint="Official x402.org settlement volume over the last 30 days." loading={loading} />
        <MetricCard label="Buyers / Sellers" value={`${stats?.buyers?.display ?? '--'} / ${stats?.sellers?.display ?? '--'}`} hint="Demand and supply sides that actually participated in x402 payments." loading={loading} />
        <MetricCard label="Public Bazaar Resources" value={formatInt(discovery?.total_resources)} hint="Discoverable paid HTTP resources returned by the Coinbase CDP x402 Bazaar API." loading={loading} />
      </div>

      <div className="mt-8 grid gap-6 lg:grid-cols-[1fr_1fr]">
        <BreakdownPanel
          title="Agentscan Payment Tags"
          rows={[
            ['Agentscan x402 agents', formatInt(agentscan?.x402_capability_agents)],
            ['AgentKit tags', formatInt(agentscan?.agentkit_capability_agents)],
            ['Payable agents', formatInt(agentscan?.payable_capability_agents)],
            ['Discovery status', discovery?.status ?? '--'],
            ['x402 version', discovery?.x402_version == null ? '--' : `v${discovery.x402_version}`],
          ]}
        />
        <CountList title="Payment Rails In Sample" rows={(discovery?.networks ?? []).map((row) => ({ ...row, name: shortNetwork(row.name) }))} />
      </div>

      <PriceDistributionChart
        rows={discovery?.price_distribution ?? []}
        sampledResources={discovery?.sampled_resources ?? 0}
        pricedResources={discovery?.priced_resources ?? 0}
        loading={loading}
      />

      <X402HistoryChart rows={scan?.history ?? []} loading={loading} />

      <div className="mt-6">
        <ResourceTable rows={discovery?.recent_resources ?? []} loading={loading} />
      </div>
    </section>
  )
}

function MetricCard({ label, value, hint, loading }: { label: string; value: string; hint: string; loading: boolean }) {
  return (
    <div title={hint} className="rounded-2xl border border-[#d6f5df] bg-white p-5 dark:border-[#143924] dark:bg-[#0d1b13]">
      <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-[#126b3a] dark:text-[#86efac]">{label}</div>
      <div className="mt-2 text-2xl font-semibold tracking-tight text-[#0a0a0a] dark:text-[#fafafa]">
        {loading ? <div className="h-7 w-24 animate-pulse rounded bg-[#d6f5df] dark:bg-[#143924]" /> : value}
      </div>
    </div>
  )
}

function BreakdownPanel({ title, rows }: { title: string; rows: [string, string][] }) {
  return (
    <div className="overflow-hidden rounded-2xl border border-[#d6f5df] dark:border-[#143924]">
      <TableTitle title={title} />
      <table className="w-full text-left text-[13px]">
        <tbody className="divide-y divide-[#d6f5df] bg-white dark:divide-[#143924] dark:bg-[#0d1b13]">
          {rows.map(([label, value]) => <InfoRow key={label} label={label} value={value} />)}
        </tbody>
      </table>
    </div>
  )
}

function CountList({ title, rows }: { title: string; rows: X402Count[] }) {
  return (
    <div className="rounded-2xl border border-[#d6f5df] bg-white p-5 dark:border-[#143924] dark:bg-[#0d1b13]">
      <h3 title="Accepted payment networks counted from the sampled Bazaar resources." className="text-sm font-semibold text-[#0a0a0a] dark:text-[#fafafa]">{title}</h3>
      <div className="mt-4 space-y-2">
        {rows.length === 0 ? <div className="text-[12px] text-[#737373]">No network sample returned.</div> : rows.slice(0, 6).map((row) => (
          <div key={row.name} title="Number of sampled Bazaar resources that accept this payment network." className="flex items-center justify-between text-[12px]">
            <span className="text-[#525252] dark:text-[#b7c9bd]">{row.name}</span>
            <span className="font-mono text-[#0a0a0a] dark:text-[#fafafa]">{formatInt(row.count)}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function ResourceTable({ rows, loading }: { rows: X402Resource[]; loading: boolean }) {
  return (
    <div className="overflow-hidden rounded-2xl border border-[#d6f5df] dark:border-[#143924]">
      <TableTitle title="Recent Bazaar Resources" />
      <table className="w-full text-left text-[13px]">
        <tbody className="divide-y divide-[#d6f5df] bg-white dark:divide-[#143924] dark:bg-[#0d1b13]">
          {loading && rows.length === 0 ? (
            <tr><td className="px-4 py-6 text-[#737373]">Loading resources...</td></tr>
          ) : rows.length === 0 ? (
            <tr><td className="px-4 py-6 text-[#737373]">No resources returned.</td></tr>
          ) : rows.map((row) => (
            <tr key={row.resource} className="transition hover:bg-[#f8fff9] dark:hover:bg-[#102218]">
              <td className="px-4 py-3">
                <a href={row.resource} target="_blank" rel="noopener noreferrer" className="font-medium text-[#0a0a0a] underline decoration-dotted underline-offset-2 dark:text-[#fafafa]">{row.host || 'resource'}</a>
                <div className="mt-0.5 line-clamp-1 text-[11px] text-[#737373]">{row.description ?? 'No description'}</div>
              </td>
              <td className="hidden px-4 py-3 text-right font-mono text-[#525252] dark:text-[#b7c9bd] md:table-cell">
                {row.method ?? '--'} · {formatMoney(row.min_price_usd)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function PriceDistributionChart({
  rows,
  sampledResources,
  pricedResources,
  loading,
}: {
  rows: X402PriceBucket[]
  sampledResources: number
  pricedResources: number
  loading: boolean
}) {
  return (
    <div className="mt-6 rounded-2xl border border-[#d6f5df] bg-white p-5 dark:border-[#143924] dark:bg-[#0d1b13]">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h3
            title="Counts Bazaar resources by the lowest accepted USD price parsed from the sampled discovery resources."
            className="text-sm font-semibold text-[#0a0a0a] dark:text-[#fafafa]"
          >
            Resource Price Distribution
          </h3>
        </div>
        <span className="text-[10px] font-medium uppercase tracking-[0.14em] text-[#126b3a] dark:text-[#86efac]">
          {formatInt(pricedResources)} / {formatInt(sampledResources)} priced
        </span>
      </div>
      <div className="mt-5 h-64">
        {loading && rows.length === 0 ? (
          <div className="h-full w-full animate-pulse rounded-xl bg-[#d6f5df] dark:bg-[#143924]" />
        ) : rows.length === 0 ? (
          <div className="flex h-full items-center justify-center text-[12px] text-[#737373]">
            No price sample returned.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={rows} margin={{ top: 10, right: 12, left: -24, bottom: 0 }}>
              <XAxis dataKey="bucket" tick={{ fontSize: 11, fill: '#737373' }} tickLine={false} axisLine={false} />
              <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: '#737373' }} tickLine={false} axisLine={false} />
              <Tooltip
                formatter={(value) => [formatInt(Number(value)), 'resources']}
                labelFormatter={(label) => `Price ${label}`}
                contentStyle={{ borderRadius: 8, borderColor: '#b7e4c7', fontSize: 12 }}
              />
              <Line type="monotone" dataKey="count" stroke="#16a34a" strokeWidth={2.5} dot={{ r: 3 }} activeDot={{ r: 5 }} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  )
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return <tr title={ROW_HINTS[label] ?? label}><td className="px-4 py-3 text-[#737373]">{label}</td><td className="px-4 py-3 text-right font-mono text-[#0a0a0a] dark:text-[#fafafa]">{value}</td></tr>
}

function TableTitle({ title }: { title: string }) {
  return <div className="bg-[#ecfdf3] px-4 py-3 text-[11px] font-medium uppercase tracking-wider text-[#126b3a] dark:bg-[#102218] dark:text-[#86efac]">{title}</div>
}

function ExternalButton({ href, children }: { href: string; children: string }) {
  return <a href={href} target="_blank" rel="noopener noreferrer" className="rounded-full bg-[#dcfce7] px-4 py-1.5 text-[#14532d] transition hover:bg-[#bbf7d0] dark:bg-[#143924] dark:text-[#86efac] dark:hover:bg-[#1b4d31]">{children}</a>
}
