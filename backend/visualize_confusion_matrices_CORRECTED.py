"""
Génère les matrices de confusion CORRECTES
Sans valeurs arbitraires de TN
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

plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

def create_confusion_matrix_correct(behavior_name, metrics, color_map):
    """Crée une matrice de confusion CORRECTE (sans TN arbitraire)"""
    tp = metrics["true_positives"]
    fp = metrics["false_positives"]
    fn = metrics["false_negatives"]
    
    # Matrice correcte: seulement TP, FP, FN (pas TN)
    # On affiche sous forme 2x2 pour clarté mais on explique
    cm = np.array([[fn, tp], [fp, 0]])  # Arrangement pour visualisation
    
    fig, ax = plt.subplots(figsize=(10, 7))
    
    # Heatmap simplifiée
    sns.heatmap(cm, annot=False, cmap=color_map, cbar=False, ax=ax)
    ax.set_xticklabels(['Ground Truth: Négatif', 'Ground Truth: Positif'])
    ax.set_yticklabels(['Prédit: Négatif', 'Prédit: Positif'])
    
    ax.set_title(f'Matrice de Confusion — {behavior_name.upper()}\n(sans True Negatives arbitraires)', 
                 fontsize=14, fontweight='bold', pad=20)
    
    # Affichage des vraies valeurs en texte
    p = metrics["precision_pct"] / 100
    r = metrics["recall_pct"] / 100
    f1 = metrics["f1_score"]
    
    text_info = (
        f'VRAIES VALEURS:\n'
        f'  TP (Vrais Positifs): {tp}\n'
        f'  FP (Faux Positifs): {fp}\n'
        f'  FN (Faux Négatifs): {fn}\n'
        f'  TN (Vrais Négatifs): NON DISPONIBLE\n\n'
        f'METRIQUES DERIVEES:\n'
        f'  Precision = TP/(TP+FP) = {tp}/({tp}+{fp}) = {p:.1%}\n'
        f'  Recall = TP/(TP+FN) = {tp}/({tp}+{fn}) = {r:.1%}\n'
        f'  F1-Score = {f1:.3f}'
    )
    
    ax.text(0.5, -0.25, text_info, transform=ax.transAxes,
           fontsize=11, ha='center', va='top', family='monospace',
           bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
    
    plt.tight_layout()
    
    output_file = f"D:/surveillance_project/docs/confusion_matrix_{behavior_name}_CORRECTED.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"[OK] Saved: {output_file}")
    plt.close()

# Génère chaque matrice corrigée
colors = {
    'fall': 'Reds',
    'crowding': 'Oranges',
    'abandoned_object': 'Greens'
}

for behavior_name, metrics in behaviors.items():
    color_map = colors.get(behavior_name, 'Blues')
    create_confusion_matrix_correct(behavior_name, metrics, color_map)

print("\n[DONE] Confusion matrices corrected and saved!")
