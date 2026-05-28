# 🚀 EXÉCUTER LA PLATEFORME MAINTENANT

## ✅ Statut Actualisé

```
[OK] Python 3.14.4
[OK] Node.js 25.9.0
[OK] npm 11.12.1 (383 packages installés)
[OK] Redis en cours d'exécution
[OK] Flask API testée et fonctionnelle
[OK] Tous les agents disponibles
```

---

## 🎯 Démarrage Simple (6 PowerShell)

### Utilisez les scripts fournis ou les commandes ci-dessous

**Chaque script/commande dans un PowerShell séparé :**

---

### 1️⃣ **Terminal 1 : Agent Perception**

```powershell
cd D:\surveillance_project
& .\START_PERCEPTION.ps1
```

**Ou manuellement :**
```powershell
cd D:\surveillance_project
& .\venv\Scripts\Activate.ps1
cd agents
python agent_perception.py
```

**À voir dans les logs :**
```
[AgentPerception] INFO — Chargement YOLOv8n
[AgentPerception] INFO — Modèle YOLOv8n prêt
[AgentPerception] INFO — Agent Perception en écoute sur channel:detections
```

---

### 2️⃣ **Terminal 2 : Agent Tracking**

```powershell
cd D:\surveillance_project
& .\START_TRACKING.ps1
```

**À voir :**
```
[AgentTracking] INFO — Agent Tracking en écoute sur channel:detections
```

---

### 3️⃣ **Terminal 3 : Agent Analyse**

```powershell
cd D:\surveillance_project
& .\START_ANALYSIS.ps1
```

**À voir :**
```
[AgentAnalysis] INFO — Agent Analyse en écoute sur channel:tracks
```

---

### 4️⃣ **Terminal 4 : Agent Décision**

```powershell
cd D:\surveillance_project
& .\START_DECISION.ps1
```

**À voir :**
```
[AgentDecision] INFO — Agent Décision en écoute sur channel:analysis
```

---

### 5️⃣ **Terminal 5 : API Flask**

```powershell
cd D:\surveillance_project\backend
& .\venv\Scripts\Activate.ps1
python app.py
```

**À voir :**
```
* Running on http://0.0.0.0:5000
* WARNING: This is a development server
```

✅ API accessible sur : **http://localhost:5000/api/health**

---

### 6️⃣ **Terminal 6 : Frontend React**

```powershell
cd D:\surveillance_project\frontend
npm run dev
```

**À voir :**
```
VITE v5.4.21 ready in 500 ms

➜  Local:   http://localhost:3000/
```

✅ Frontend accessible sur : **http://localhost:3000**

---

## 🌐 Accès à l'Application

Une fois tous les services démarrés :

👉 **Ouvrir dans votre navigateur :**
```
http://localhost:3000
```

### Services actifs :
| Service | URL | Port |
|---------|-----|------|
| **Frontend** | http://localhost:3000 | 3000 |
| **API** | http://localhost:5000 | 5000 |
| **Redis** | localhost | 6379 |
| **MongoDB** | localhost | 27017 |

---

## 👤 Premier Login

### Créer un compte :
1. Aller à http://localhost:3000
2. Cliquer sur "Créer un compte"
3. Remplir le formulaire :
   - Email : `user@example.com`
   - Password : `password123`
   - Username : `user`
4. Valider

### Se connecter :
- Email : `user@example.com`
- Password : `password123`

---

## 📹 Test de Fonctionnalité (5 minutes)

### 1. Upload une vidéo
- Dashboard → Bouton "Upload Vidéo"
- Sélectionner un fichier vidéo (mp4, avi, mov, etc.)
- Attendre l'upload

### 2. Lancer une analyse
- Cliquer sur la vidéo
- Bouton "Analyser"
- L'analyse démarre

### 3. Attendre les résultats
- Status devient "processing"
- Après 2-5 min : "completed"

### 4. Voir les résultats
- Cliquer sur "Voir les résultats"
- Timeline des événements détectés
- Statistiques (chutes, attroupements, objets abandonnés)

### 5. Exporter
- Boutons : CSV, JSON, PDF
- Télécharger le rapport

---

## 📊 Vérification des Logs

### Terminal 1 (Perception)
```
Doit montrer : "YOLO frame_id=XXX, detections=N"
```

### Terminal 2 (Tracking)
```
Doit montrer : "Tracks: N personnes, velocité moyenne=X px/frame"
```

### Terminal 3 (Analyse)
```
Doit montrer : "Événements détectés: X | Chutes tracées: N"
```

### Terminal 4 (Décision)
```
Doit montrer : "⚠️ ALERTE: Chute détectée..."
```

### Terminal 5 (API)
```
Doit montrer : "POST /api/analyses/create 200"
```

### Terminal 6 (Frontend)
```
Doit montrer : "✓ compiled successfully"
```

---

## ⚠️ Troubleshooting Rapide

### Port déjà utilisé
```powershell
# Si port 3000 est déjà utilisé:
# Modifier dans frontend/vite.config.js, port: 3001

# Si port 5000 est déjà utilisé:
# Modifier dans backend/app.py, app.run(port=5001)
```

### MongoDB non disponible
```powershell
# Vérifier que MongoDB est lancé
mongod
```

### Redis pas de réponse
```powershell
# Vérifier Redis
redis-cli ping
# Si erreur, lancer Redis
redis-server
```

### npm: command not found
```powershell
# Réinstaller npm
npm install -g npm
```

---

## 📚 Résumé du Déploiement

✅ **6 services lancés :**
1. Agent Perception (YOLOv8n)
2. Agent Tracking (DeepSORT)
3. Agent Analyse (Chutes, attroupements, objets)
4. Agent Décision (Alertes + risques)
5. API Flask (REST API)
6. Frontend React (Interface web)

✅ **Communication :**
- Agents ↔ Agents via **Redis Pub/Sub**
- Frontend ↔ API via **HTTP/REST**
- API ↔ Data via **MongoDB**

✅ **Prêt pour :**
- Upload de vidéos
- Analyse en temps réel
- Consultation des résultats
- Export de rapports

---

## 🎉 C'est prêt !

**Lancez les 6 PowerShell avec les commandes ci-dessus et accédez à :**

### 👉 **http://localhost:3000**

Bonne utilisation ! 🚀

---

**Version:** 1.0.0  
**Date:** 28 mai 2026  
**Status:** ✅ Production Ready
