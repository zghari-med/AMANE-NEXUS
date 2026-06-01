import json
import os

BENCHMARK_PATH = os.path.join(
    os.path.dirname(__file__),
    "data", "benchmark_results.json"
)

with open(BENCHMARK_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

behaviors = data["by_behavior"]

def print_confusion_matrix(behavior_name, metrics):
    tp = metrics["true_positives"]
    fp = metrics["false_positives"]
    fn = metrics["false_negatives"]
    tn = 100
    
    p = metrics["precision_pct"] / 100
    r = metrics["recall_pct"] / 100
    f1 = metrics["f1_score"]
    
    print("\n" + "="*60)
    print("  " + behavior_name.upper())
    print("="*60)
    print("\n                 PREDICTION")
    print("            Negative | Positive")
    print("         -----------+----------")
    print(f"Real Negative|   {tn:3d}   |  {fp:3d}  ")
    print("         -----------+----------")
    print(f"    Positive |  {fn:3d}   |  {tp:3d}  ")
    print("         -----------+----------")
    
    print(f"\nMetrics:")
    print(f"   TP: {tp:2d}  FP: {fp:2d}  FN: {fn:2d}  TN: {tn:3d}")
    print(f"   Precision: {p:6.1%} | Recall: {r:6.1%} | F1: {f1:.3f}")

for behavior_name, metrics in behaviors.items():
    print_confusion_matrix(behavior_name, metrics)

# Matrice globale
print("\n\n" + "="*60)
print("  GLOBAL (MICRO-AVERAGE)")
print("="*60)

tp_global = sum(b["true_positives"] for b in behaviors.values())
fp_global = sum(b["false_positives"] for b in behaviors.values())
fn_global = sum(b["false_negatives"] for b in behaviors.values())

p_global = data["model_accuracy"]["global"]["precision_pct"] / 100
r_global = data["model_accuracy"]["global"]["recall_pct"] / 100
f1_global = data["model_accuracy"]["global"]["f1_score"]

print(f"\n                 PREDICTION")
print(f"            Negative | Positive")
print(f"         -----------+----------")
print(f"Real Negative|   300  |  {fp_global:3d}  ")
print(f"         -----------+----------")
print(f"    Positive |  {fn_global:3d}   |  {tp_global:3d}  ")
print(f"         -----------+----------")

print(f"\nGlobal Metrics:")
print(f"   TP: {tp_global:2d}  FP: {fp_global:2d}  FN: {fn_global:2d}")
print(f"   Precision: {p_global:6.1%} | Recall: {r_global:6.1%} | F1: {f1_global:.3f}")

print("\n" + "="*60 + "\n")
