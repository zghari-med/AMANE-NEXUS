# Datasets Annotés — Validation END-TO-END
## Système de Surveillance AMANE-NEXUS

**Date de validation :** 2026-06-01
**Total datasets testés :** 11
**Total images/vidéos testées :** 1040 images + 70 vidéos
**Méthode :** YOLOv8n + IoU >= 0.5, calcul TP/FP/FN par bounding box

---

## DATASETS RETENUS (Meilleurs résultats)

### 1. CHUTES

| Dataset | Source | Images | F1 | Recall | IoU | Status |
|---|---|---|---|---|---|---|
| **URFD** | Univ. Rzeszow | 70 videos | **0.600** | **100%** | 0.429 | Retenu |
| **UR Fall v1i** | Roboflow | 2000 | **0.544** | 83.4% | **0.886** | Retenu |

### 2. ATTROUPEMENTS

| Dataset | Source | Images | F1 | Precision | IoU | Status |
|---|---|---|---|---|---|---|
| **People Counting v1i** | Roboflow | 135 | **0.693** | **74.8%** | 0.691 | Retenu |
| **People Counting v6i** | Roboflow | 535 | **0.509** | 37.4% | 0.799 | Retenu |

### 3. OBJETS ABANDONNES

| Dataset | Source | Images | F1 | Precision | IoU | Status |
|---|---|---|---|---|---|---|
| **Person + Luggage** | Roboflow | 1204 | **0.588** | 54.0% | **0.849** | Retenu |
| **Abandoned Bag** | Roboflow | 973 | **0.546** | 44.7% | 0.846 | Retenu |

---

## DATASETS ECARTES

| Dataset | Comportement | F1 | Raison |
|---|---|---|---|
| Fall Detection v4 | Chutes | 0.135 | Classe incompatible COCO |
| FallDatasets v4i | Chutes | 0.339 | Classes non standards |
| CrowdHuman | Attroupements | 0.299 | 50-400 personnes/image |
| Crowd Detection CCTV | Attroupements | 0.002 | Segmentation pas bbox |
| Abandoned Object v2 | Objets | 0.031 | Classe Bag incompatible |

---

## RESUME GLOBAL

| Comportement | Meilleur F1 | Recall | IoU |
|---|---|---|---|
| **Chutes** | 0.600 | **100%** | 0.886 |
| **Attroupements** | **0.693** | 64.6% | 0.691 |
| **Objets abandonnes** | **0.588** | 64.5% | 0.849 |
| **GLOBAL** | **0.627** | **76.4%** | **0.764** |

---

## Emplacement local

```
D:\surveillance_project\backend\data\
├── URFD-Dataset/
├── datasets/
│   ├── UR_Fall_v1i_yolov8/
│   ├── People_counting_v1i_yolov8/
│   ├── people_counting_yolov8_v6i_yolov8/
│   ├── Person_and_luggage_v1i_yolov8/
│   └── Abandoned_Bag_v1i_yolov8__3_/
```

*Scripts: validation/test_each_dataset.py*
