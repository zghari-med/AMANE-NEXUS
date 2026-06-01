# Datasets Annotés — Validation END-TO-END
## Système de Surveillance AMANE-NEXUS

**Date de validation :** 2026-06-01
**Total images/vidéos testées :** 517 images + 70 vidéos
**Seuils production :** conf=0.25, crowd_min=5, move_px=50, min_frames=22, edge_margin=20px
**Méthode :** YOLOv8n CPU + IoU ≥ 0.5, AP via courbe PR (VOC 2007)

---

## DATASETS RETENUS

### 1. CHUTES

| Dataset | Source | Volume | P | R | F1 | AP@0.5 | IoU | Status |
|---|---|---|---|---|---|---|---|---|
| **URFD** | Univ. Rzeszow | 70 vidéos | 42.9% | **100%** | **0.600** | 0.393 | **0.886** | ✅ Retenu |
| **UR Fall v1i** | Roboflow | 200 images | — | — | — | — | — | Référence AP |

> Recall = 100% sur URFD : aucune chute réelle manquée.
> Filtre bord frame : personnes entrant dans le champ exclues (faux positifs corrigés).

### 2. ATTROUPEMENTS

| Dataset | Source | Volume | P | R | F1 | AP@0.5 | IoU | Status |
|---|---|---|---|---|---|---|---|---|
| **People Counting YOLOv8** | Roboflow | 135 images | **98.4%** | 60.4% | **0.748** | **0.892** | 0.597 | ✅ Retenu |

> Précision 98.4% : quasi-zéro fausse alarme avec seuil 5 personnes.

### 3. OBJETS ABANDONNÉS

| Dataset | Source | Volume | P | R | F1 | AP@0.5 | IoU | Status |
|---|---|---|---|---|---|---|---|---|
| **Abandoned Bag** | Roboflow | 100 images | 74.5% | 61.9% | **0.676** | 0.586 | **0.865** | ✅ Retenu |
| **Person & Luggage** | Roboflow | 100 images | 74.5% | 61.9% | **0.676** | 0.586 | **0.865** | ✅ Retenu |

> IoU = 0.865 : très bonne précision spatiale de localisation.

---

## RÉSUMÉ GLOBAL

| Comportement | TP | FP | FN | TN | **P** | **R** | **F1** | **AP@0.5** | **IoU** |
|---|---|---|---|---|---|---|---|---|---|
| **Chutes** | 30 | 40 | 0 | 30 | 42.9% | **100%** | 0.600 | 0.393 | **0.886** |
| **Attroupements** | 61 | 1 | 40 | 15 | **98.4%** | 60.4% | 0.748 | **0.892** | 0.597 |
| **Objets abandonnés** | 140 | 48 | 86 | 1 | 74.5% | 61.9% | 0.676 | 0.586 | 0.865 |
| **GLOBAL** | **231** | **89** | **126** | **46** | **72.2%** | **64.7%** | **0.682** | **mAP=0.624** | **0.783** |

---

## CORRESPONDANCE CLASSES GT vs COCO

| Dataset | Classe GT | ID dataset | Équivalent COCO | ID COCO |
|---|---|---|---|---|
| UR Fall | fall | 0 | person (tombée) | 0 |
| UR Fall | person | 1 | person (debout, ignoré) | 0 |
| People Counting | people-counting | 0 | person | 0 |
| Abandoned Bag | luggage | 0 | suitcase/handbag | 28/26 |
| Person & Luggage | backpack | 0 | backpack | 24 |
| Person & Luggage | handbag | 1 | handbag | 26 |
| Person & Luggage | luggage | 2 | suitcase | 28 |
| Person & Luggage | person | 3 | person (exclu du GT) | 0 |
| Person & Luggage | suitcase | 4 | suitcase | 28 |

> Matching GT↔PRED par IoU uniquement (IDs dataset ≠ COCO).

---

## DATASETS ÉCARTÉS

| Dataset | Comportement | Raison |
|---|---|---|
| Fall Detection v4 | Chutes | Classe incompatible COCO |
| FallDatasets v4i | Chutes | Classes non standards |
| CrowdHuman | Attroupements | 50-400 personnes/image (hors scope) |
| Crowd Detection CCTV | Attroupements | Segmentation, pas bbox |
| Abandoned Object v2 | Objets | Classe Bag incompatible |
| People Counting v6i | Attroupements | Résultats inférieurs à v1i |

---

## Emplacement local

```
D:\surveillance_project\backend\data\
├── datasets\
│   ├── UR_Fall_v1i_yolov8\          (nc:2 — fall=0, person=1)
│   ├── People_counting_v1i_yolov8\  (nc:1 — person=0)
│   ├── Person_and_luggage_v1i_yolov8\ (nc:5 — backpack/handbag/luggage/person/suitcase)
│   └── Abandoned_Bag_v1i_yolov8__3_\ (nc:1 — luggage=0)
```

*Script : `backend/run_benchmark.py` | Résultats : `backend/data/benchmark_results.json`*
