/**
 * BenchmarkChart — visualise les résultats de benchmark YOLO
 * (temps d'inférence, FPS, par comportement).
 */
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, ReferenceLine,
} from 'recharts'

export default function BenchmarkChart({ benchmarks }) {
  if (!benchmarks) {
    return (
      <div className="flex items-center justify-center h-40 text-gray-400 text-sm">
        Chargement des benchmarks…
      </div>
    )
  }

  // Graphe 1 : performances par comportement (P/R/F1)
  const byBehavior = benchmarks.by_behavior ? Object.entries(benchmarks.by_behavior).map(
    ([key, v]) => ({
      name: v.label || key,
      Précision: v.precision_pct,
      Rappel:    v.recall_pct,
      F1:        v.f1_score ? Math.round(v.f1_score * 100) : 0,
    })
  ) : []

  // Graphe 2 : tempos CPU par vidéo
  const procBench = benchmarks.processing_benchmarks
    ? Object.entries(benchmarks.processing_benchmarks).map(([k, v]) => ({
        name: k,
        Durée: v.duration_s,
        Traitement: v.processing_time_s,
      }))
    : []

  return (
    <div className="space-y-8">
      {/* P/R/F1 par comportement */}
      {byBehavior.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-gray-700 mb-3">
            Précision / Rappel / F1 par comportement (%)
          </h4>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={byBehavior} margin={{ left: -10, right: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="name" tick={{ fontSize: 11 }} />
              <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
              <Tooltip formatter={(v) => `${v}%`} />
              <Legend iconSize={10} />
              <ReferenceLine y={85} stroke="#94a3b8" strokeDasharray="4 2"
                             label={{ value: '85%', position: 'right', fontSize: 10 }} />
              <Bar dataKey="Précision" fill="#3b82f6" radius={[3,3,0,0]} />
              <Bar dataKey="Rappel"    fill="#22c55e" radius={[3,3,0,0]} />
              <Bar dataKey="F1"        fill="#8b5cf6" radius={[3,3,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Durée vs Traitement par vidéo */}
      {procBench.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-gray-700 mb-3">
            Durée vidéo vs Temps de traitement (secondes)
          </h4>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={procBench} margin={{ left: -10, right: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="name" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Legend iconSize={10} />
              <Bar dataKey="Durée"      fill="#94a3b8" radius={[3,3,0,0]} />
              <Bar dataKey="Traitement" fill="#f59e0b" radius={[3,3,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}
