import { motion } from 'framer-motion'
import { TrendingUp, TrendingDown } from 'lucide-react'

const ICON_STYLES = {
  blue:   { bg: 'bg-brand-100',  icon: 'text-brand-600'  },
  purple: { bg: 'bg-purple-100', icon: 'text-purple-600' },
  green:  { bg: 'bg-green-100',  icon: 'text-green-600'  },
  red:    { bg: 'bg-red-100',    icon: 'text-red-500'    },
  orange: { bg: 'bg-orange-100', icon: 'text-orange-500' },
  teal:   { bg: 'bg-teal-100',   icon: 'text-teal-600'   },
}

export default function StatCard({
  title,
  value,
  icon: Icon,
  color = 'blue',
  trend = null,
  description = '',
}) {
  const style = ICON_STYLES[color] ?? ICON_STYLES.blue

  return (
    <motion.div
      whileHover={{ y: -2, boxShadow: '14px 17px 40px 4px rgba(112,144,176,0.22)' }}
      transition={{ duration: 0.2 }}
      className="bg-white rounded-2xl p-5 shadow-horizon"
    >
      <div className="flex items-center justify-between">
        {/* Left — text */}
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium text-secondaryGray-600 uppercase tracking-wide mb-1.5">
            {title}
          </p>
          <p className="text-3xl font-bold text-navy-700 leading-none tracking-tight">
            {value}
          </p>

          {trend !== null && (
            <div className="flex items-center gap-1 mt-2">
              {trend > 0
                ? <TrendingUp size={13} className="text-green-500" />
                : <TrendingDown size={13} className="text-red-400" />
              }
              <span className={`text-xs font-semibold ${trend > 0 ? 'text-green-500' : 'text-red-400'}`}>
                {trend > 0 ? '+' : ''}{trend}%
              </span>
              {description && (
                <span className="text-xs text-secondaryGray-600 ml-1">{description}</span>
              )}
            </div>
          )}

          {!trend && description && (
            <p className="text-xs text-secondaryGray-600 mt-1.5">{description}</p>
          )}
        </div>

        {/* Right — icon */}
        <div className={`${style.bg} w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0 ml-4`}>
          <Icon size={22} className={style.icon} />
        </div>
      </div>
    </motion.div>
  )
}
