/**
 * Configuration centralisée de l'API AMANE-NEXUS
 * Modifier cette constante pour changer l'URL du backend dans toute l'application
 */
export const API = import.meta.env.VITE_API_URL || 'http://localhost:5000'

/**
 * Génère l'URL d'une capture annotée avec le token JWT en query param.
 * Les balises <img> ne supportent pas les headers — on passe le token dans l'URL.
 * @param {string} filename  - Nom du fichier capture
 * @param {string} token     - JWT Bearer token
 * @returns {string}         - URL avec ?token=...
 */
export const captureUrl = (filename, token) =>
  `${API}/api/captures/${filename}${token ? `?token=${token}` : ''}`
