# FAQ Soutenance — 20 Questions-Réponses pour le Jury
## PFE MSID-TAM — Surveillance Intelligente Multi-Agent

---

### Q1 — Pourquoi avoir choisi YOLOv8 plutôt qu'une autre architecture ?

**Réponse :** YOLOv8 (You Only Look Once v8) a été retenu pour trois raisons principales :
1. **Vitesse** : architecture single-stage, un seul passage du réseau suffit pour détecter ET classer (contrairement à Faster R-CNN qui est two-stage)
2. **Compromis accuracy/vitesse** : YOLOv8n (nano, 6.2 Mo) atteint 37.3 mAP@50 sur COCO tout en fonctionnant à ~5 FPS sur CPU sans GPU
3. **Écosystème** : Ultralytics fournit une API Python mature, bien documentée, avec pré-entraînement sur 80 classes COCO suffisant pour notre domaine

---

### Q2 — Qu'est-ce que le F1-score et pourquoi cette métrique est-elle pertinente ?

**Réponse :** Le F1-score est la **moyenne harmonique** de la Précision et du Rappel :
```
F1 = 2 × Précision × Rappel / (Précision + Rappel)
```
Il est pertinent car il pénalise les systèmes qui maximisent l'une aux dépens de l'autre. Dans la surveillance, les deux erreurs ont du coût :
- **Faux positif (FP)** : alerte intempestive → fatigue de l'opérateur
- **Faux négatif (FN)** : incident manqué → danger non détecté

Notre système obtient F1 = **0.627** validé sur 11 datasets annotés réels, avec Recall = **100%** sur les chutes (URFD) et F1 = **0.693** pour les attroupements.

---

### Q3 — Comment avez-vous calibré les seuils de détection ?

**Réponse :** Calibration empirique en 3 étapes :
1. **Analyse des ratios** : exécution de YOLO sur les vidéos de test pour mesurer les distributions réelles (personnes debout : ratio h/w ~ 2.5-3.5 ; tombées : ~ 0.4-0.6)
2. **Tests itératifs** : ajustement du seuil de 0.55 → 0.80 → 0.65 selon les faux positifs observés
3. **Validation** : vérification manuelle frame-by-frame sur les timestamps d'alertes

L'historique de calibration est documenté dans `benchmark_results.json`.

---

### Q4 — Pourquoi MongoDB plutôt qu'une base de données relationnelle ?

**Réponse :** MongoDB a été choisi pour :
- **Flexibilité du schéma** : les alertes et timelines varient en structure selon le type d'événement
- **Documents imbriqués** : `events_timeline` est naturellement un tableau JSON
- **Scalabilité horizontale** : sharding natif pour des déploiements à grande échelle
- **Compatibilité** : driver PyMongo direct sans ORM lourd (évite mongoengine incompatible avec Python 3.14+)

---

### Q5 — Comment fonctionne l'authentification JWT ?

**Réponse :** JSON Web Token (JWT) est un standard RFC 7519 :
1. L'utilisateur envoie email/mot de passe → serveur vérifie avec bcrypt
2. Le serveur génère un token signé HMAC-SHA256 contenant `{user_id, role, exp}`
3. Le client stocke le token dans localStorage (Zustand persist)
4. Chaque requête envoie le token dans `Authorization: Bearer <token>`
5. Le décorateur `@token_required` valide la signature et l'expiration

Durée de vie : **24 heures**. Le mot de passe n'est jamais stocké en clair (bcrypt + sel).

---

### Q6 — Comment le système évite-t-il les alertes dupliquées ?

**Réponse :** Système de **cooldown par type d'événement** :
- Le dictionnaire `last_alert = {'fall': -9999, 'crowding': -9999, 'abandoned': -9999}` stocke le numéro de frame de la dernière alerte
- Avant de créer une alerte : `(frame_id - last_alert[type]) > COOLDOWN`
- Le cooldown est mis à jour **immédiatement** quand l'événement est détecté (avant la boucle de sauvegarde), pour éviter les doubles détections dans la même frame
- Valeurs : Fall=300f (~10s), Crowd=90f (~3s), Abandoned=900f (~30s)

---

### Q7 — Expliquez le principe de l'architecture multi-agent

**Réponse :** Un système multi-agent est composé d'**agents autonomes** qui coopèrent pour résoudre un problème complexe. Chaque agent :
- A une **spécialisation** (perception, tracking, analyse...)
- Agit de façon **indépendante** dans son domaine
- **Communique** avec les autres via des interfaces bien définies

Notre architecture sépare les responsabilités : l'agent YOLO ne connaît pas les règles métier ; l'agent de décision ne sait pas comment détecter les objets. Cette séparation facilite la **maintenabilité** et l'**extensibilité**.

---

### Q8 — Quelle est la différence entre Précision et Rappel ?

**Réponse :**
- **Précision** = TP / (TP + FP) : "Parmi toutes nos alertes, combien étaient réelles ?" → mesure la qualité des détections positives
- **Rappel** = TP / (TP + FN) : "Parmi tous les incidents réels, combien avons-nous détectés ?" → mesure la complétude

Notre système validé sur 11 datasets réels :
- **Chutes** : Précision = 42.9%, Rappel = **100%** → aucune chute manquée (URFD, 70 vidéos)
- **Attroupements** : Précision = **74.8%**, Rappel = 64.6% (People Counting, 135 images)
- **Objets abandonnés** : Précision = 54.0%, Rappel = 64.5% (Person+Luggage, 200 images)

Pour la surveillance, le **rappel est critique** : un incident manqué peut être dangereux. Notre Recall=100% sur les chutes valide ce critère.

---

### Q9 — Comment fonctionne le tracking des objets abandonnés ?

**Réponse :** Algorithme basé sur une grille de cellules :
1. La frame est divisée en cellules de 100×100 px
2. Chaque objet portable (sac, valise...) est associé à une clé `{classe}_{cx//100}_{cy//100}`
3. À chaque frame, le déplacement de l'objet est calculé
4. Si déplacement < 50px sur ≥ 22 frames traitées → alerte
5. La cellule de 100px absorbe les micro-variations de détection (stabilité)

---

### Q10 — Pourquoi React + Tailwind plutôt qu'Angular ou Vue ?

**Réponse :**
- **React 18** : écosystème très large, composants réutilisables, hooks modernes (useState, useEffect, useCallback, useRef)
- **Tailwind CSS** : utilitaire-first, no CSS custom nécessaire, responsive intégré, cohérence visuelle
- **Zustand** (vs Redux) : plus simple, moins de boilerplate pour l'état global (auth store persisté)
- **Recharts** : bibliothèque de graphes SVG, bien intégrée avec React, responsive

---

### Q11 — Comment avez-vous mesuré les performances du système ?

**Réponse :** Protocole de benchmark documenté dans `benchmark_results.json` :
1. **Inférence YOLO** : 100 runs sur frames 640×640, mesure du temps wall-clock
2. **Accuracy** : annotation manuelle de 6 vidéos de test (54 événements), comparaison aux détections automatiques
3. **API** : mesure des temps de réponse via curl sur 100 requêtes
4. **MongoDB** : profiler MongoDB pour les queries

---

### Q12 — Quelles sont les limites actuelles du système ?

**Réponse :** Limites identifiées :
1. **Temps réel limité** : ~5 FPS sur CPU (vs caméra 30 FPS) → nécessite GPU pour temps réel
2. **Calibration vidéo-dépendante** : seuils optimisés pour des caméras en surplomb
3. **Pas de tracking ré-ID** : si une personne sort du champ puis revient, nouvel identifiant
4. **Pas de nuit/infrarouge** : modèle entraîné sur images diurnes
5. **Attroupement limité** : seuil de 5 personnes, distances en pixels (dépend de la résolution)

---

### Q13 — Comment le système gère-t-il plusieurs utilisateurs simultanément ?

**Réponse :**
- **Isolation des données** : chaque user ne voit que ses propres vidéos (`uploaded_by: user_id`)
- **Rôles** : admin (accès global) vs user (accès limité aux propres ressources)
- **Thread d'analyse** : chaque analyse lance un thread daemon indépendant
- **Polling** : le frontend poll l'état toutes les 3 secondes, pas de WebSocket (suffisant pour analyses différées)
- **MongoDB** : gère la concurrence nativement

---

### Q14 — Expliquez votre choix de FRAME_SKIP=3

**Réponse :** FRAME_SKIP=3 signifie qu'on analyse 1 frame sur 3 :
- **Gain CPU** : 67% de réduction de charge
- **Couverture temporelle** : à 30 FPS, une frame toutes les 100ms → événements de moins de 100ms seront manqués (acceptable pour chutes/attroupements qui durent plusieurs secondes)
- **FPS effectif** : 5.2 FPS × 3 = 15.6 FPS équivalents couverts
- **Compromis** : validé empiriquement → aucun événement manqué sur nos vidéos de test

---

### Q15 — Comment sont sécurisées les données utilisateur ?

**Réponse :**
- **Mots de passe** : bcrypt avec sel aléatoire, facteur de coût 10 (2^10 = 1024 itérations)
- **JWT** : signé HMAC-SHA256 avec clé secrète serveur, expiration 24h
- **CORS** : Flask-CORS configuré (en prod : restreindre aux domaines autorisés)
- **Isolation données** : queries MongoDB filtrées sur `user_id`
- **Upload** : `werkzeug.secure_filename` pour éviter path traversal, extensions whitelistées

---

### Q16 — Qu'est-ce que Pandas apporte dans ce projet ?

**Réponse :** Pandas permet une analyse statistique structurée des alertes :
- **groupby()** : agrégation par type d'événement, par date, par semaine
- **value_counts()** : distribution des types d'alertes
- **DataFrame** : manipulation tabulaire efficace sur les données MongoDB
- **Régression linéaire** (numpy.polyfit) : calcul de la tendance (pente) par type d'événement
- **Export CSV** : `to_csv()` pour les métriques exportables

---

### Q17 — Comment serait déployé le système en production ?

**Réponse :** Pipeline de déploiement prévu :
1. **Docker multi-stage** : image finale Python 3.10-slim + Nginx (frontend servi statiquement)
2. **Docker Compose** : orchestration locale (MongoDB + Redis + Backend + Frontend)
3. **Variables d'environnement** : `MONGO_URI`, `SECRET_KEY`, `REDIS_HOST` via `.env`
4. **Healthchecks** : MongoDB, Redis, Flask, Frontend
5. **En cloud** : migration vers Kubernetes avec HPA pour scalabilité horizontale
6. **GPU** : ajout d'une instance avec CUDA pour inférence temps réel

---

### Q18 — Quelle est la valeur ajoutée de l'AnalyticsEngine ?

**Réponse :** L'AnalyticsEngine (couche Data Science) apporte :
- **Tendances** : identification des pics d'activité par heure/semaine
- **Métriques objectives** : Précision/Rappel/F1 calculés et documentés scientifiquement
- **Cache intelligent** : TTL de 1h pour éviter les recalculs fréquents (Pandas est plus lent que MongoDB)
- **Export** : données exportables en CSV pour analyse externe
- **Réutilisabilité** : séparation nette entre logique métier (Flask) et analyse (Pandas)

---

### Q19 — Comment avez-vous testé le système ?

**Réponse :** Approche multi-niveaux :
1. **Tests unitaires Python** (pytest) : `test_analytics.py`, `test_benchmarks.py` — valident la logique métier
2. **Tests manuels** : annotation frame-by-frame des vidéos de test (cam1, video1) pour mesurer accuracy
3. **Tests API** : curl + Postman pour valider chaque endpoint
4. **CI/CD** : pipeline GitHub Actions automatique (lint + tests + validation benchmarks + build)
5. **Tests de non-régression** : re-analyse après chaque modification de seuil

---

### Q20 — Quelles améliorations futures envisagez-vous ?

**Réponse :** Roadmap future :
1. **GPU** : utilisation de YOLOv8m ou YOLOv8l avec CUDA → temps réel (30+ FPS)
2. **Pose estimation** : YOLOv8-pose pour détection de chute basée sur keypoints (plus robuste que ratio bbox)
3. **Caméras multiples** : pipeline Redis Pub/Sub pour traitement de flux concurrents
4. **Alertes SMS/Email** : intégration Twilio/SendGrid pour notification en temps réel
5. **Apprentissage actif** : labeling des faux positifs pour re-entraîner le modèle
6. **Détection de bagarre** : two-person proximity + rapid motion
7. **Dashboard temps réel** : WebSocket au lieu de polling toutes les 3s
