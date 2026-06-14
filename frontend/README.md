# AMANE-NEXUS — Frontend

Interface React 18 pour le système de surveillance intelligente multi-agent.

## Stack

| Technologie | Version | Rôle |
|---|---|---|
| React | 18.2.0 | UI composants |
| Vite | 5.0.7 | Bundler + dev server (HMR) |
| Tailwind CSS | 3.3.6 | Styles utilitaires |
| Recharts | 2.10.3 | Graphiques (tendances, statistiques) |
| Zustand | 4.4.1 | Store JWT — état d'authentification |
| Axios | via services/api.js | Client HTTP centralisé |

## Structure

```
frontend/
├── src/
│   ├── main.jsx               # Point d'entrée React
│   ├── App.jsx                # Router + ProtectedRoute
│   ├── index.css              # Styles globaux Tailwind
│   ├── context/
│   │   └── authStore.js       # Zustand store (token JWT, user, logout)
│   ├── services/
│   │   └── api.js             # Client Axios — baseURL + intercepteurs auth
│   ├── pages/
│   │   ├── LoginPage.jsx      # Formulaire login + gestion erreur
│   │   ├── VideosPage.jsx     # Upload, liste, aperçu, analyse
│   │   ├── AnalysisPage.jsx   # Résultats YOLOv8, alertes, captures
│   │   ├── StatisticsPage.jsx # Graphiques Recharts, export CSV
│   │   ├── DashboardAdminPage.jsx  # Vue admin (caméras, métriques)
│   │   ├── UsersPage.jsx      # Gestion utilisateurs (admin only)
│   │   └── ProfilePage.jsx    # Profil utilisateur
│   └── components/            # Composants réutilisables
├── public/
├── package.json
├── vite.config.js
└── tailwind.config.js
```

## Démarrage local

```bash
npm install
npm run dev
# Interface disponible sur http://localhost:3000
```

L'API backend doit être accessible sur `http://localhost:5000`. Le proxy Vite redirige automatiquement les appels `/api/*` vers le backend.

## Scripts

| Commande | Description |
|---|---|
| `npm run dev` | Dev server avec HMR |
| `npm run build` | Build production dans `dist/` |
| `npm run preview` | Aperçu du build production |
| `npm run lint` | ESLint |

## Pages

| Page | Route | Rôle |
|---|---|---|
| Login | `/login` | Authentification — obtient le JWT |
| Vidéos | `/videos` | Upload vidéo, aperçu thumbnail, lancer analyse |
| Analyse | `/analysis/:id` | Résultats, alertes annotées, tendances |
| Statistiques | `/statistics` | Graphiques globaux, export CSV |
| Dashboard Admin | `/admin` | Vue caméras, métriques système |
| Utilisateurs | `/users` | CRUD utilisateurs (admin only) |
| Profil | `/profile` | Informations du compte connecté |

## Authentification

Le store Zustand (`authStore.js`) persiste le JWT en `localStorage`. Le client Axios injecte automatiquement le header `Authorization: Bearer <token>` sur chaque requête.

Pour les flux vidéo (`<video src="...">`) le token est passé en query string `?token=<jwt>` car les balises `<video>` du navigateur ne peuvent pas envoyer de headers personnalisés.

## Build Docker

L'image multi-stage utilise `node:18-alpine` pour le build puis `nginx:alpine` pour servir les fichiers statiques. Le `nginx.conf` à la racine du projet gère le reverse proxy vers le backend.

```bash
# Depuis la racine du projet
docker compose build frontend
docker compose up -d frontend
```
