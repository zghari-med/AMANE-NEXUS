#!/usr/bin/env python3
"""
Télécharger et extraire UR Fall Detection Dataset complet (70 séquences)
30 chutes (fall-01..30) + 40 ADL (adl-01..40) — caméra RGB cam0 uniquement
Source : https://fenix.ur.edu.pl/~mkepski/ds/uf.html
"""
import urllib.request
import zipfile
import os
import sys
import time
from pathlib import Path

BASE_URL = "https://fenix.ur.edu.pl/~mkepski/ds/data/"
DEST = Path(__file__).parent / "data" / "URFD-Dataset"
DEST.mkdir(parents=True, exist_ok=True)

FALL_SEQUENCES = [f"fall-{i:02d}-cam0-rgb.zip" for i in range(1, 31)]
ADL_SEQUENCES  = [f"adl-{i:02d}-cam0-rgb.zip"  for i in range(1, 41)]
ALL_SEQUENCES  = FALL_SEQUENCES + ADL_SEQUENCES

print("=" * 70)
print("  TELECHARGEMENT UR FALL DETECTION DATASET")
print("=" * 70)
print(f"  Total      : {len(ALL_SEQUENCES)} fichiers")
print(f"  Chutes     : {len(FALL_SEQUENCES)} (fall-01..30)")
print(f"  ADL        : {len(ADL_SEQUENCES)}  (adl-01..40)")
print(f"  Destination: {DEST}")
print(f"  Taille     : ~1.5 GB total (~55 MB / fichier)")
print("=" * 70 + "\n")

downloaded = 0
extracted  = 0
failed     = 0
skipped    = 0

for i, seq in enumerate(ALL_SEQUENCES, 1):
    url          = BASE_URL + seq
    zip_path     = DEST / seq
    folder_name  = seq.replace("-cam0-rgb.zip", "")
    extract_path = DEST / folder_name

    seq_type = "CHUTE" if seq.startswith("fall") else "ADL  "
    prefix   = f"[{i:2d}/{len(ALL_SEQUENCES)}] {seq_type} | {seq}"

    # Sauter si déjà extrait
    if extract_path.exists() and any(extract_path.rglob("*.png")):
        print(f"{prefix} -> DEJA EXTRAIT, skip")
        skipped += 1
        downloaded += 1
        extracted  += 1
        continue

    # --- Téléchargement ---
    t0 = time.time()
    try:
        print(f"{prefix}")
        print(f"         Telechargement...", end="", flush=True)

        def _progress(block, block_size, total):
            done = block * block_size
            if total > 0:
                pct = min(done / total * 100, 100)
                mb  = done / 1024 / 1024
                print(f"\r         Telechargement... {pct:5.1f}%  {mb:.1f} MB", end="", flush=True)

        urllib.request.urlretrieve(url, str(zip_path), reporthook=_progress)
        elapsed = time.time() - t0
        size_mb = zip_path.stat().st_size / 1024 / 1024
        print(f"\r         Telechargement OK  {size_mb:.1f} MB  ({elapsed:.0f}s)")
        downloaded += 1

    except Exception as e:
        print(f"\r         ERREUR telechargement : {e}")
        failed += 1
        continue

    # --- Extraction ---
    try:
        print(f"         Extraction...", end="", flush=True)
        with zipfile.ZipFile(str(zip_path), "r") as z:
            z.extractall(str(DEST))
        print(" OK")
        extracted += 1
        zip_path.unlink()          # supprimer le ZIP
        print(f"         ZIP supprime")
    except Exception as e:
        print(f" ERREUR extraction : {e}")
        failed += 1
        continue

print("\n" + "=" * 70)
print("  RESUME")
print("=" * 70)
print(f"  Telecharges : {downloaded}/{len(ALL_SEQUENCES)}")
print(f"  Extraits    : {extracted}/{len(ALL_SEQUENCES)}")
print(f"  Sautes      : {skipped}  (deja presents)")
print(f"  Echoues     : {failed}")

if failed == 0:
    print(f"\n  Dataset pret dans : {DEST}")
    print(f"\n  Lancer les tests :")
    print(f"    cd D:/surveillance_project/backend")
    print(f"    python tests/test_falls.py")
else:
    print(f"\n  {failed} fichier(s) ont echoue — relancez le script (skip auto).")

print("=" * 70 + "\n")
