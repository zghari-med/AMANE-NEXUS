import { useState, useEffect } from 'react'
import Sidebar from '../components/Sidebar'
import MetricsCard from '../components/MetricsCard'
import BenchmarkChart from '../components/BenchmarkChart'
import { Cpu, Zap, Target, Clock } from 'lucide-react'

const API = 'http://localhost:5000'

export default function BenchmarksPage() {
  const [data, setData]     = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]   = useState(null)

  useEffect(() => {
    fetch(`${API}/api/analyses/benchmarks`)
      .then(r => r.json())
      .then(d => { setData(d); setLoading(false) })
      .catch(e => { setError(e.message); setLoading(false) })
  }, [])

  const yolo   = data?.yolo_inference_benchmarks
  const acc    = data?.model_accuracy?.global
  const env    = data?.environment

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar />

      <div className="flex-1 overflow-auto">
        <div className="bg-white border-b sticky top-0 z-10">
          <div className="max-w-7xl mx-auto px-6 py-5">
            <h1 className="text-2xl font-bold text-gray-900">Benchmarks YOLO</h1>
            <p className="text-gray-500 text-sm">Résultats de performance mesurés — modèle YOLOv8n</p>
          </div>
        </div>

        <div className="max-w-7xl mx-auto px-6 py-8">

          {loading && (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin w-10 h-10 border-4 border-blue-600 border-t-transparent rounded-full" />
            </div>
          )}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-red-700">
              Erreur : {error}
            </div>
          )}

          {data && !loading && (
            <>
              {/* Métriques globales */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-5 mb-8">
                <MetricsCard
                  label="F1-Score"
                  value={acc?.f1_score ? acc.f1_score * 100 : 0}
                  color="purple"
                  subtitle="Moyenne harmonique P/R"
                />
                <MetricsCard
                  label="Précision"
                  value={acc?.precision_pct || 0}
                  color="blue"
                  subtitle="TP / (TP + FP)"
                />
                <MetricsCard
                  label="Rappel"
                  value={acc?.recall_pct || 0}
                  color="green"
                  subtitle="TP / (TP + FN)"
                />
              </div>

              {/* KPIs inférence */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-5 mb-8">
                {[
                  {
                    icon: Clock,  bg: 'bg-blue-50',   text: 'text-blue-700',
                    label: 'Inférence moy.',
                    value: yolo ? `${yolo.avg_inference_ms} ms` : '—',
                  },
                  {
                    icon: Zap,    bg: 'bg-yellow-50', text: 'text-yellow-700',
                    label: 'FPS effectif',
                    value: yolo ? `${yolo.avg_fps} FPS` : '—',
                  },
                  {
                    icon: Zap,    bg: 'bg-green-50',  text: 'text-green-700',
                    label: 'FPS avec SKIP×3',
                    value: yolo ? `${yolo.effective_fps_with_skip3} FPS` : '—',
                  },
                  {
                    icon: Target, bg: 'bg-purple-50', text: 'text-purple-700',
                    label: 'mAP@50',
                    value: acc ? `${Math.round((data?.model_accuracy?.global?.map50 || 0) * 100)}%` : '—',
                  },
                ].map(({ icon: Icon, bg, text, label, value }) => (
                  <div key={label} className={`${bg} rounded-xl p-5 border border-white shadow-sm`}>
                    <div className="flex items-center gap-2 mb-2">
                      <Icon size={18} className={text} />
                      <p className="text-sm text-gray-600">{label}</p>
                    </div>
                    <p className={`text-2xl font-bold ${text}`}>{value}</p>
                  </div>
                ))}
              </div>

              {/* Graphes benchmarks */}
              <div className="bg-white rounded-xl shadow-sm border p-6 mb-6">
                <h3 className="font-semibold text-gray-900 mb-5">Performance par comportement</h3>
                <BenchmarkChart benchmarks={data} />
              </div>

              {/* Tableau détaillé par comportement */}
              <div className="bg-white rounded-xl shadow-sm border p-6 mb-6">
                <h3 className="font-semibold text-gray-900 mb-4">Détail par comportement</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 border-b">
                      <tr>
                        {['Comportement', 'TP', 'FP', 'FN', 'Précision', 'Rappel', 'F1', 'Notes'].map(h => (
                          <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">
                            {h}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {data.by_behavior && Object.entries(data.by_behavior).map(([key, v]) => (
                        <tr key={key} className="hover:bg-gray-50">
                          <td className="px-4 py-3 font-medium text-gray-900">{v.label || key}</td>
                          <td className="px-4 py-3 text-green-600 font-semibold">{v.true_positives}</td>
                          <td className="px-4 py-3 text-red-500">{v.false_positives}</td>
                          <td className="px-4 py-3 text-orange-500">{v.false_negatives}</td>
                          <td className="px-4 py-3">
                            <span className="bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full text-xs font-bold">
                              {v.precision_pct}%
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <span className="bg-green-100 text-green-700 px-2 py-0.5 rounded-full text-xs font-bold">
                              {v.recall_pct}%
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <span className="bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full text-xs font-bold">
                              {Math.round(v.f1_score * 100)}%
                            </span>
                          </td>
                          <td className="px-4 py-3 text-xs text-gray-500 max-w-xs truncate">
                            {v.notes || '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Environnement */}
              {env && (
                <div className="bg-white rounded-xl shadow-sm border p-6">
                  <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
                    <Cpu size={18} className="text-gray-500" />
                    Environnement de test
                  </h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    {[
                      ['OS',          env.os],
                      ['Python',      env.python_version],
                      ['CPU',         env.cpu],
                      ['RAM',         `${env.ram_gb} Go`],
                      ['Modèle YOLO', env.yolo_model],
                      ['Taille',      `${env.model_size_mb} Mo`],
                      ['Résolution',  env.input_resolution],
                      ['Device',      env.device],
                    ].map(([k, v]) => (
                      <div key={k} className="bg-gray-50 rounded-lg p-3">
                        <p className="text-xs text-gray-400 uppercase font-semibold mb-1">{k}</p>
                        <p className="font-medium text-gray-900">{v}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
