/**
 * MetricsCard — affiche une métrique scientifique (F1, Précision, Rappel)
 * avec une jauge circulaire SVG et un label coloré.
 */
export default function MetricsCard({ label, value, color = 'blue', subtitle = '' }) {
  const COLORS = {
    blue:   { ring: '#3b82f6', bg: 'bg-blue-50',   text: 'text-blue-700' },
    green:  { ring: '#22c55e', bg: 'bg-green-50',  text: 'text-green-700' },
    red:    { ring: '#ef4444', bg: 'bg-red-50',    text: 'text-red-700' },
    orange: { ring: '#f59e0b', bg: 'bg-orange-50', text: 'text-orange-700' },
    purple: { ring: '#8b5cf6', bg: 'bg-purple-50', text: 'text-purple-700' },
  }
  const c      = COLORS[color] ?? COLORS.blue
  const pct    = Math.min(100, Math.max(0, parseFloat(value) || 0))
  const radius = 30
  const circ   = 2 * Math.PI * radius
  const dash   = (pct / 100) * circ

  return (
    <div className={`${c.bg} rounded-xl p-5 flex items-center gap-4 border border-white shadow-sm`}>
      {/* SVG gauge */}
      <svg width={80} height={80} viewBox="0 0 80 80" className="shrink-0">
        <circle cx={40} cy={40} r={radius} fill="none" stroke="#e5e7eb" strokeWidth={8} />
        <circle
          cx={40} cy={40} r={radius} fill="none"
          stroke={c.ring} strokeWidth={8}
          strokeDasharray={`${dash} ${circ}`}
          strokeDashoffset={circ * 0.25}
          strokeLinecap="round"
          style={{ transition: 'stroke-dasharray 0.8s ease' }}
        />
        <text x={40} y={44} textAnchor="middle"
              fontSize={15} fontWeight="bold" fill={c.ring}>
          {pct}%
        </text>
      </svg>
      <div>
        <p className={`text-lg font-bold ${c.text}`}>{label}</p>
        {subtitle && <p className="text-sm text-gray-500 mt-0.5">{subtitle}</p>}
      </div>
    </div>
  )
}
