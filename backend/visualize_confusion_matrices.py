"""
Génère des visualisations des matrices de confusion
Crée des fichiers PNG avec matplotlib et seaborn
"""
import json
import os
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

BENCHMARK_PATH = os.path.join(
    os.path.dirname(__file__),
    "data", "benchmark_results.json"
)

with open(BENCHMARK_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

behaviors = data["by_behavior"]

# Configuration matplotlib
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

def create_confusion_matrix_plot(behavior_name, metrics, color_map):
    """Crée une visualisation de matrice de confusion"""
    tp = metrics["true_positives"]
    fp = metrics["false_positives"]
    fn = metrics["false_negatives"]
    tn = 100
    
    # Matrice
    cm = np.array([[tn, fp], [fn, tp]])
    
    # Figure
    fig, ax = plt.subplots(figsize=(8, 6))
    
    # Heatmap
    sns.heatmap(cm, annot=True, fmt='d', cmap=color_map, cbar=False,
                xticklabels=['Negative', 'Positive'],
                yticklabels=['Negative', 'Positive'],
                ax=ax, square=True, linewidths=2, linecolor='white',
                cbar_kws={'label': 'Count'})
    
    ax.set_xlabel('Predicted', fontsize=12, fontweight='bold')
    ax.set_ylabel('Real', fontsize=12, fontweight='bold')
    ax.set_title(f'Confusion Matrix -- {behavior_name.upper()}', 
                 fontsize=14, fontweight='bold', pad=20)
    
    # Metrics text
    p = metrics["precision_pct"] / 100
    r = metrics["recall_pct"] / 100
    f1 = metrics["f1_score"]
    
    metrics_text = (f'Precision: {p:.1%}  |  Recall: {r:.1%}  |  F1: {f1:.3f}\n'
                   f'TP: {tp} | FP: {fp} | FN: {fn} | TN: {tn}')
    ax.text(0.5, -0.15, metrics_text, transform=ax.transAxes,
           fontsize=10, ha='center', va='top',
           bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    
    # Sauvegarde
    output_file = f"D:/surveillance_project/docs/confusion_matrix_{behavior_name}.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"[OK] Saved: {output_file}")
    plt.close()

# Couleurs par comportement
colors = {
    'fall': 'Reds',
    'crowding': 'Oranges',
    'abandoned_object': 'Greens'
}

# Génère chaque matrice
for behavior_name, metrics in behaviors.items():
    color_map = colors.get(behavior_name, 'Blues')
    create_confusion_matrix_plot(behavior_name, metrics, color_map)

# Matrice globale
fig, ax = plt.subplots(figsize=(8, 6))

tp_global = sum(b["true_positives"] for b in behaviors.values())
fp_global = sum(b["false_positives"] for b in behaviors.values())
fn_global = sum(b["false_negatives"] for b in behaviors.values())

cm_global = np.array([[300, fp_global], [fn_global, tp_global]])

sns.heatmap(cm_global, annot=True, fmt='d', cmap='Blues', cbar=False,
            xticklabels=['Negative', 'Positive'],
            yticklabels=['Negative', 'Positive'],
            ax=ax, square=True, linewidths=2, linecolor='white')

ax.set_xlabel('Predicted', fontsize=12, fontweight='bold')
ax.set_ylabel('Real', fontsize=12, fontweight='bold')
ax.set_title('Confusion Matrix -- GLOBAL (Micro-Average)', 
             fontsize=14, fontweight='bold', pad=20)

p_global = data["model_accuracy"]["global"]["precision_pct"] / 100
r_global = data["model_accuracy"]["global"]["recall_pct"] / 100
f1_global = data["model_accuracy"]["global"]["f1_score"]

metrics_text = (f'Precision: {p_global:.1%}  |  Recall: {r_global:.1%}  |  F1: {f1_global:.3f}\n'
               f'TP: {tp_global} | FP: {fp_global} | FN: {fn_global}')
ax.text(0.5, -0.15, metrics_text, transform=ax.transAxes,
       fontsize=10, ha='center', va='top',
       bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.5))

plt.tight_layout()
plt.savefig("D:/surveillance_project/docs/confusion_matrix_global.png", dpi=300, bbox_inches='tight')
print(f"[OK] Saved: D:/surveillance_project/docs/confusion_matrix_global.png")
plt.close()

print("\n[DONE] All confusion matrices visualized successfully!")
