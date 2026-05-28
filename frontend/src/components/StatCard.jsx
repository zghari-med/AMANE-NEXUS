import { motion } from 'framer-motion'

export default function StatCard({
  title,
  value,
  icon: Icon,
  color = 'blue',
  trend = null,
  description = ''
}) {
  const colorClasses = {
    blue: 'bg-blue-50 text-blue-600',
    purple: 'bg-purple-50 text-purple-600',
    green: 'bg-green-50 text-green-600',
    red: 'bg-red-50 text-red-600',
    orange: 'bg-orange-50 text-orange-600',
  }

  return (
    <motion.div
      whileHover={{ y: -4 }}
      className="card p-6"
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-gray-600 text-sm font-medium">{title}</p>
          <p className="text-3xl font-bold text-gray-900 mt-2">{value}</p>
          {description && <p className="text-gray-500 text-xs mt-1">{description}</p>}
          {trend && (
            <div className="mt-3 flex items-center gap-2">
              <span className={`text-xs font-medium ${trend > 0 ? 'text-green-600' : 'text-red-600'}`}>
                {trend > 0 ? '+' : ''}{trend}%
              </span>
            </div>
          )}
        </div>
        <div className={`${colorClasses[color]} p-3 rounded-lg`}>
          <Icon size={24} />
        </div>
      </div>
    </motion.div>
  )
}
