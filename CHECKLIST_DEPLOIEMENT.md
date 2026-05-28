# ✅ Checklist de Déploiement

## Avant de Démarrer (Prérequis)

### Système & Infrastructure
- [ ] Python 3.10+ installé
- [ ] Node.js 18+ installé
- [ ] MongoDB 6+ en cours d'exécution (sur `localhost:27017`)
- [ ] Redis 6+ en cours d'exécution (sur `localhost:6379`)
- [ ] Au minimum 2GB RAM disponible
- [ ] Au moins 10GB d'espace disque

### Vérification Prérequis
```bash
# Lancer ces commandes et vérifier les versions
python --version
node --version
npm --version
mongosh --version
redis-cli --version
```

---

## Installation (Étapes Séquentielles)

### Étape 1: Configuration Environnement
- [ ] Vérifier que `.env` existe à la racine du projet
- [ ] Vérifier les valeurs dans `.env` :
  ```
  SECRET_KEY=pfe_surveillance_2026
  MONGO_URI=mongodb://localhost:27017/surveillance_db
  REDIS_HOST=localhost
  REDIS_PORT=6379
  ```
- [ ] Créer les dossiers s'ils n'existent pas :
  - [ ] `backend/uploads/`
  - [ ] `backend/exports/`

### Étape 2: Backend Python
- [ ] Naviguer vers le dossier `backend`
- [ ] Créer l'environnement virtuel: `python -m venv venv`
- [ ] Activer l'environnement virtuel
  - Windows: `venv\Scripts\activate`
  - Linux/Mac: `source venv/bin/activate`
- [ ] Installer les dépendances: `pip install -r requirements.txt`
- [ ] Vérifier l'installation: `pip list | grep -E "Flask|mongoengine|redis"`

### Étape 3: Frontend Node.js
- [ ] Naviguer vers le dossier `frontend`
- [ ] Installer les dépendances: `npm install`
- [ ] Vérifier les packages: `npm list react react-router-dom`

---

## Démarrage Agents & Serveurs

### Préparation: Ouvrir 6 Terminaux

**Terminal 1: Agent Perception**
```bash
cd backend
source venv/Scripts/activate
python agents/agent_perception.py
```
✅ Attendus dans les logs:
- "Chargement YOLOv8n"
- "Modèle YOLOv8n prêt"
- "Connecté à Redis ✓"
- "Agent Perception en écoute"

**Terminal 2: Agent Tracking**
```bash
cd backend
source venv/Scripts/activate
python agents/agent_tracking.py
```
✅ Attendus dans les logs:
- "Connecté à Redis ✓"
- "Initialisation DeepSORT"
- "Agent Tracking en écoute"

**Terminal 3: Agent Analyse**
```bash
cd backend
source venv/Scripts/activate
python agents/agent_analysis.py
```
✅ Attendus dans les logs:
- "Connecté à Redis ✓"
- "Agent Analyse en écoute"

**Terminal 4: Agent Décision**
```bash
cd backend
source venv/Scripts/activate
python agents/agent_decision.py
```
✅ Attendus dans les logs:
- "Connecté à Redis ✓"
- "Agent Décision en écoute"

**Terminal 5: API Flask**
```bash
cd backend
source venv/Scripts/activate
python app.py
```
✅ Attendus dans les logs:
- "✓ MongoDB connecté"
- "Running on http://0.0.0.0:5000"

**Terminal 6: Frontend React**
```bash
cd frontend
npm run dev
```
✅ Attendus dans les logs:
- "VITE v5.0.7 ready"
- "Local: http://localhost:3000/"

---

## Vérification Post-Démarrage

### Tester la Connectivité

#### Redis
```bash
# Dans un nouveau terminal
redis-cli
> PING
PONG  ✓

> SUBSCRIBE channel:detections
# Devrait afficher les messages en direct
```
- [ ] Redis répond à PING
- [ ] SUBSCRIBE fonctionne
- [ ] Voir les messages détections

#### MongoDB
```bash
# Nouveau terminal
mongosh
> db.version()
6.0.0  ✓

> use surveillance_db
> db.users.find()
# Devrait retourner une liste vide ou utilisateurs
```
- [ ] MongoDB se connecte
- [ ] Bonne version
- [ ] Base `surveillance_db` existe

#### API Flask
```bash
# Nouveau terminal
curl http://localhost:5000/api/health
# Doit retourner: {"status":"healthy"}
```
- [ ] API répond sur 5000
- [ ] Health check OK
- [ ] CORS configuré

#### Frontend React
- [ ] Ouvrir http://localhost:3000
- [ ] Page de login s'affiche
- [ ] Pas d'erreurs console (F12)
- [ ] Pas d'erreurs réseau

---

## Premier Utilisateur & Test

### Créer un Compte Admin

**Via l'API (curl)**
```bash
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@surveillance.com",
    "password": "admin123",
    "username": "admin",
    "full_name": "Administrateur"
  }'
```
✅ Réponse attendue:
```json
{
  "message": "User registered successfully",
  "user": {
    "email": "admin@surveillance.com",
    "username": "admin",
    "role": "user"
  }
}
```

**Via le Frontend**
- [ ] Aller à http://localhost:3000/register
- [ ] Remplir le formulaire d'enregistrement
- [ ] Cliquer "Créer un compte"
- [ ] Être redirigé vers /login

### Se Connecter
- [ ] Aller à http://localhost:3000/login
- [ ] Entrer les credentials (email, password)
- [ ] Cliquer "Se connecter"
- [ ] Être redirigé vers le dashboard
- [ ] Dashboard charge correctement

### Test Basique Vidéo
- [ ] Dashboard affiché
- [ ] Bouton "Upload Vidéo" visible
- [ ] Cliquer et sélectionner un fichier vidéo
- [ ] Vidéo s'affiche dans la liste
- [ ] Bouton "Analyser" présent

### Lancer une Analyse
- [ ] Cliquer "Analyser" sur une vidéo
- [ ] Voir le statut changer en "processing"
- [ ] Attendre la fin du traitement
- [ ] Voir le statut changer en "completed"
- [ ] Événements détectés s'affichent

### Exporter des Données
- [ ] Cliquer sur "Voir les résultats"
- [ ] Page d'analyse s'ouvre
- [ ] Boutons Export visibles (CSV, JSON, PDF)
- [ ] Cliquer export CSV → fichier téléchargé
- [ ] Fichier contient des données

---

## Vérifications Finales

### Performance
- [ ] Agent Perception: FPS > 20
- [ ] Agent Tracking: Pas de lag
- [ ] API: Réponse < 500ms
- [ ] Frontend: Pas de lag UI

### Sécurité
- [ ] Login/Register fonctionnent
- [ ] JWT tokens générés correctement
- [ ] Routes protégées bloquent sans token
- [ ] Admin/User permissions respectées

### Données
- [ ] MongoDB stocke les vidéos
- [ ] MongoDB stocke les analyses
- [ ] MongoDB stocke les alertes
- [ ] Export CSV/JSON/PDF créent les fichiers

### Notifications
- [ ] Alertes générées s'affichent
- [ ] Alertes stockées en MongoDB
- [ ] Timeline des alertes affichée
- [ ] Statut des alertes modifiable

---

## Dépannage Rapide

### Issue: "Connexion MongoDB refusée"
```bash
# Vérifier que MongoDB tourne
mongosh

# Si erreur, démarrer MongoDB
mongod

# Si sur Docker: docker start <container>
```

### Issue: "Redis connexion failed"
```bash
# Vérifier Redis
redis-cli ping

# Si erreur, démarrer Redis
redis-server

# Si sur Docker: docker start <container>
```

### Issue: "Port 5000 déjà utilisé"
```bash
# Trouver le processus
lsof -i :5000

# Tuer le processus
kill -9 <PID>

# Ou utiliser un autre port dans app.py
app.run(port=5001)
```

### Issue: "Port 3000 déjà utilisé"
```bash
# Modifier dans vite.config.js
server: {
  port: 3001,  // ou un autre port libre
}
```

### Issue: "Agents ne se connectent pas à Redis"
```bash
# Vérifier REDIS_HOST et REDIS_PORT dans .env
REDIS_HOST=localhost
REDIS_PORT=6379

# Tester la connexion
redis-cli -h localhost -p 6379 ping
# Doit retourner: PONG
```

---

## Après Déploiement

### Optimisations Recommandées
- [ ] Réduire `FRAME_SKIP` si vous voulez + de précision (vs performance)
- [ ] Ajuster les seuils de détection selon votre cas d'usage
- [ ] Configurer les notifications (email, Slack, etc.)
- [ ] Mettre en place la sauvegarde MongoDB

### Monitoring
- [ ] Vérifier les logs régulièrement
- [ ] Monitorer l'utilisation CPU/RAM
- [ ] Monitorer la taille de la base MongoDB
- [ ] Monitorer les alertes générées

### Maintenance
- [ ] Nettoyer les vidéos anciennes
- [ ] Archiver les analyses terminées
- [ ] Mettre à jour les dépendances (pip, npm)
- [ ] Sauvegarder MongoDB régulièrement

---

## Production Checklist (Bonus)

- [ ] Utiliser `ProductionConfig` dans config.py
- [ ] HTTPS/SSL configuré
- [ ] CORS configuré pour le domaine
- [ ] MongoDB Replica Set configuré
- [ ] Redis persistance activée (RDB/AOF)
- [ ] Logs structurés (JSON)
- [ ] Monitoring (Prometheus/Grafana)
- [ ] Alertes SMS/Email configurées
- [ ] Rate limiting sur l'API
- [ ] Backup automatique MongoDB

---

## Support & Aide

**En Cas de Problème:**
1. Consulter `GUIDE_DEMARRAGE.md` (dépannage détaillé)
2. Consulter `ARCHITECTURE.md` (comprendre le flux)
3. Vérifier les logs de chaque terminal
4. Vérifier les variables `.env`
5. Tester les connexions Redis/MongoDB séparément

---

**Statut: ✅ Prêt à Déployer !**

Durée estimée de déploiement complet: **15-20 minutes**  
Temps de première analyse: **2-5 minutes** (selon taille vidéo)

