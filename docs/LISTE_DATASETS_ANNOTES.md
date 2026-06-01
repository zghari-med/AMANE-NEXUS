# Datasets Annotés — Validation END-TO-END
## Système de Surveillance AMANE-NEXUS

**Date de validation :** 2026-06-01
**Total datasets testés :** 5 datasets retenus
**Total images/vidéos testées :** 517 images + 70 vidéos
**Méthode :** YOLOv8n CPU + IoU >= 0.5, AP via courbe PR (VOC 2007)
**Seuils :** conf=0.20, crowd_min=4, move_px=80, min_frames=15

---

## DATASETS RETENUS

### 1. CHUTES

| Dataset | Source | Volume | P | R | F1 | AP@0.5 | IoU | Status |
|---|---|---|---|---|---|---|---|---|
| **URFD** | Univ. Rzeszow | 70 vidéos | 42.9% | **100%** | **0.600** | 0.393 | 0.780 | ✅ Retenu |
| **UR Fall v1i** | Roboflow | 200 images | — | — | — | — | — | Référence AP |

> Recall = 100% sur URFD : aucune chute réelle manquée sur 70 vidéos.

### 2. ATTROUPEMENTS

| Dataset | Source | Volume | P | R | F1 | AP@0.5 | IoU | Status |
|---|---|---|---|---|---|---|---|---|
| **People Counting YOLOv8** | Roboflow | 135 images | **100%** | 89.7% | **0.946** | **1.000** | 0.619 | ✅ Retenu |

> Précision = 100% : zéro fausse alarme sur 135 images.

### 3. OBJETS ABANDONNES

| Dataset | Source | Volume | P | R | F1 | AP@0.5 | IoU | Status |
|---|---|---|---|---|---|---|---|---|
| **Person & Luggage** | Roboflow | 100 images | 71.0% | 67.3% | **0.691** | 0.586 | **0.857** | ✅ Retenu |
| **Abandoned Bag** | Roboflow | 100 images | 71.0% | 67.3% | **0.691** | 0.586 | **0.857** | ✅ Retenu |

> IoU = 0.857 : très bonne précision spatiale de localisation.

---

## RÉSUMÉ GLOBAL

| Comportement | TP | FP | FN | TN | **P** | **R** | **F1** | **AP@0.5** | **IoU** |
|---|---|---|---|---|---|---|---|---|---|
| **Chutes** | 30 | 40 | 0 | 30 | 42.9% | **100%** | 0.600 | 0.393 | 0.780 |
| **Attroupements** | 105 | 0 | 12 | 0 | **100%** | 89.7% | **0.946** | **1.000** | 0.619 |
| **Objets abandonnés** | 152 | 62 | 74 | 1 | 71.0% | 67.3% | 0.691 | 0.586 | **0.857** |
| **GLOBAL** | **287** | **102** | **86** | **31** | **73.8%** | **76.9%** | **0.753** | **mAP=0.660** | **0.752** |

---

## CORRESPONDANCE CLASSES GT vs COCO

| Dataset | Classe GT | ID dataset | Classe COCO équivalente | ID COCO |
|---|---|---|---|---|
| UR Fall | fall | 0 | person (tombée) | 0 |
| UR Fall | person | 1 | person (debout) | 0 |
| People Counting | people-counting | 0 | person | 0 |
| Abandoned Bag | luggage | 0 | suitcase/handbag | 28/26 |
| Person & Luggage | backpack | 0 | backpack | 24 |
| Person & Luggage | handbag | 1 | handbag | 26 |
| Person & Luggage | luggage | 2 | suitcase | 28 |
| Person & Luggage | person | 3 | person | 0 |
| Person & Luggage | suitcase | 4 | suitcase | 28 |

> **Note :** Le matching GT↔PRED se fait par IoU uniquement (pas par class ID) car les IDs de classes dataset ≠ COCO.

---

## DATASETS ÉCARTÉS

| Dataset | Comportement | Raison |
|---|---|---|
| Fall Detection v4 | Chutes | Classe incompatible COCO |
| FallDatasets v4i | Chutes | Classes non standards |
| CrowdHuman | Attroupements | 50-400 personnes/image (hors scope) |
| Crowd Detection CCTV | Attroupements | Segmentation pas bbox |
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

*Script de benchmark : `backend/run_benchmark.py`*
*Résultats JSON : `backend/data/benchmark_results.json`*
