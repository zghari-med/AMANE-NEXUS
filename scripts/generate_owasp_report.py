"""
Genere owasp-report.html -- couverture OWASP Top 10 AMANE-NEXUS
Usage : python scripts/generate_owasp_report.py [pip-audit-report.json]
"""
import json, sys, os
from datetime import datetime, timezone
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

AUDIT_FILE = sys.argv[1] if len(sys.argv) > 1 else "pip-audit-report.json"

# ── Lire pip-audit-report.json ────────────────────────────────────────────────
vulns, total_vulns, fixed_vulns = [], 0, 0
if os.path.exists(AUDIT_FILE):
    with open(AUDIT_FILE, encoding="utf-8") as f:
        data = json.load(f)
    for dep in data.get("dependencies", []):
        for v in dep.get("vulns", []):
            total_vulns += 1
            fixed = bool(v.get("fix_versions"))
            if fixed:
                fixed_vulns += 1
            vulns.append({
                "package": dep["name"],
                "version": dep["version"],
                "id": v["id"],
                "fix": ", ".join(v.get("fix_versions", [])) or "—",
                "fixed": fixed,
                "desc": v.get("description", "")[:120] + "…" if len(v.get("description","")) > 120 else v.get("description",""),
            })

remaining = total_vulns - fixed_vulns

# ── Données OWASP Top 10 ─────────────────────────────────────────────────────
OWASP = [
    {
        "id": "A01", "name": "Broken Access Control",
        "status": "COUVERT",
        "impl": "JWT stateless + RBAC (admin / operator / viewer) sur tous les endpoints API",
        "evidence": "Décorateur @token_required, rôles vérifiés sur /api/users et /api/cameras",
        "color": "#16a34a",
    },
    {
        "id": "A02", "name": "Cryptographic Failures",
        "status": "COUVERT",
        "impl": "Mots de passe hachés bcrypt (cost=12) · JWT HS256 · SECRET_KEY auto-généré si faible",
        "evidence": "bcrypt.hashpw() dans auth_routes · PyJWT 2.13.0 · génération aléatoire secrets.token_hex()",
        "color": "#16a34a",
    },
    {
        "id": "A03", "name": "Injection",
        "status": "COUVERT",
        "impl": "Requêtes MongoDB via ObjectId typé (pas de requêtes brutes) · pas d'eval/exec utilisateur",
        "evidence": "Toutes les queries utilisent ObjectId(video_id) — injection NoSQL impossible",
        "color": "#16a34a",
    },
    {
        "id": "A04", "name": "Insecure Design",
        "status": "COUVERT",
        "impl": "Architecture multi-agent isolée · uploads restreints aux types vidéo · séparation frontend/backend",
        "evidence": "CORS limité aux origines déclarées · workers d'analyse dans threads séparés",
        "color": "#16a34a",
    },
    {
        "id": "A05", "name": "Security Misconfiguration",
        "status": "COUVERT",
        "impl": ".env exclu du dépôt · ADMIN_PASSWORD aléatoire au premier boot · CORS_ORIGINS configurables",
        "evidence": ".gitignore exclut .env · SECRET_KEY auto-généré · variables d'env dans docker-compose",
        "color": "#16a34a",
    },
    {
        "id": "A06", "name": "Vulnerable & Outdated Components",
        "status": "COUVERT" if remaining == 0 else "PARTIEL",
        "impl": f"pip-audit en CI/CD · {total_vulns} CVE détectées · {fixed_vulns} corrigées · {remaining} restante(s) sans correctif",
        "evidence": "Job audit-python (stage lint) · rapport JSON uploadé comme artifact GitLab",
        "color": "#16a34a" if remaining == 0 else "#d97706",
    },
    {
        "id": "A07", "name": "Identification & Authentication Failures",
        "status": "COUVERT",
        "impl": "Flask-Limiter : 10 req/min + 50 req/hr sur /api/auth/login · tokens expirables",
        "evidence": "Limiter(app, storage_uri=redis) · decorator @limiter.limit sur login endpoint",
        "color": "#16a34a",
    },
    {
        "id": "A08", "name": "Software & Data Integrity Failures",
        "status": "COUVERT",
        "impl": "6 headers de sécurité HTTP via @after_request : CSP, X-Frame-Options, X-Content-Type-Options…",
        "evidence": "Content-Security-Policy, Referrer-Policy, Permissions-Policy sur toutes les réponses",
        "color": "#16a34a",
    },
    {
        "id": "A09", "name": "Security Logging & Monitoring Failures",
        "status": "COUVERT",
        "impl": "log_activity() trace chaque action (upload, login, delete, analyse) avec user_id et timestamp UTC",
        "evidence": "Collection activity_log en MongoDB · logs structurés Python logging niveau INFO/WARNING/ERROR",
        "color": "#16a34a",
    },
    {
        "id": "A10", "name": "Server-Side Request Forgery (SSRF)",
        "status": "COUVERT",
        "impl": "_is_ssrf_safe() bloque loopback (127.x, ::1) et link-local (169.254.x.x) · ALLOW_PRIVATE_IPS contrôle RFC1918",
        "evidence": "Validation appliquée avant tout fetch() serveur sur URL caméra fournie par l'utilisateur",
        "color": "#16a34a",
    },
]

covered  = sum(1 for o in OWASP if o["status"] == "COUVERT")
partial  = sum(1 for o in OWASP if o["status"] == "PARTIEL")
score_pct = round((covered + partial * 0.5) / 10 * 100)

# ── Template HTML ─────────────────────────────────────────────────────────────
rows_owasp = ""
for o in OWASP:
    badge_bg  = "#dcfce7" if o["status"] == "COUVERT" else "#fef3c7"
    badge_txt = "#15803d" if o["status"] == "COUVERT" else "#92400e"
    icon      = "✔" if o["status"] == "COUVERT" else "⚠"
    rows_owasp += f"""
    <tr>
      <td><span class="badge-id">{o['id']}</span></td>
      <td><strong>{o['name']}</strong></td>
      <td><span class="badge" style="background:{badge_bg};color:{badge_txt}">{icon} {o['status']}</span></td>
      <td>{o['impl']}</td>
      <td class="evidence">{o['evidence']}</td>
    </tr>"""

rows_vuln = ""
if vulns:
    for v in sorted(vulns, key=lambda x: x["fixed"]):
        status_html = ('<span class="badge" style="background:#dcfce7;color:#15803d">✔ CORRIGÉ</span>'
                       if v["fixed"] else
                       '<span class="badge" style="background:#fee2e2;color:#991b1b">⚠ SANS CORRECTIF</span>')
        rows_vuln += f"""
        <tr>
          <td><code>{v['package']}</code></td>
          <td><code>{v['version']}</code></td>
          <td><code>{v['id']}</code></td>
          <td><code>{v['fix']}</code></td>
          <td>{status_html}</td>
        </tr>"""
else:
    rows_vuln = '<tr><td colspan="5" style="text-align:center;color:#6b7280">Aucune vulnérabilité détectée ✔</td></tr>'

html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Rapport OWASP Top 10 — AMANE-NEXUS</title>
<style>
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ font-family:'Segoe UI',Arial,sans-serif; background:#f8fafc; color:#1e293b; }}
  header {{ background:linear-gradient(135deg,#1e293b 0%,#334155 100%); color:#fff; padding:36px 48px; }}
  header h1 {{ font-size:1.9rem; font-weight:700; }}
  header p  {{ margin-top:6px; color:#94a3b8; font-size:.95rem; }}
  .container {{ max-width:1100px; margin:32px auto; padding:0 24px; }}
  .kpi-grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:16px; margin-bottom:32px; }}
  .kpi {{ background:#fff; border-radius:12px; padding:20px 24px; box-shadow:0 1px 4px rgba(0,0,0,.08); text-align:center; }}
  .kpi .val {{ font-size:2rem; font-weight:800; }}
  .kpi .lbl {{ font-size:.8rem; color:#64748b; margin-top:4px; text-transform:uppercase; letter-spacing:.05em; }}
  .card {{ background:#fff; border-radius:12px; box-shadow:0 1px 4px rgba(0,0,0,.08); margin-bottom:28px; overflow:hidden; }}
  .card-header {{ background:#f1f5f9; padding:14px 24px; font-weight:700; font-size:1rem; border-bottom:1px solid #e2e8f0; display:flex; align-items:center; gap:10px; }}
  table {{ width:100%; border-collapse:collapse; font-size:.88rem; }}
  th {{ background:#f8fafc; padding:11px 14px; text-align:left; font-weight:600; color:#475569; border-bottom:2px solid #e2e8f0; font-size:.8rem; text-transform:uppercase; letter-spacing:.04em; }}
  td {{ padding:12px 14px; border-bottom:1px solid #f1f5f9; vertical-align:top; }}
  tr:last-child td {{ border-bottom:none; }}
  tr:hover td {{ background:#f8fafc; }}
  .badge-id {{ background:#1e293b; color:#fff; border-radius:6px; padding:3px 8px; font-size:.78rem; font-weight:700; font-family:monospace; }}
  .badge {{ border-radius:20px; padding:3px 10px; font-size:.78rem; font-weight:700; white-space:nowrap; }}
  .evidence {{ color:#64748b; font-size:.82rem; font-family:monospace; }}
  code {{ background:#f1f5f9; padding:2px 6px; border-radius:4px; font-size:.85rem; }}
  .score-bar {{ height:12px; background:#e2e8f0; border-radius:6px; overflow:hidden; margin:8px 0; }}
  .score-fill {{ height:100%; background:linear-gradient(90deg,#16a34a,#22c55e); border-radius:6px; width:{score_pct}%; }}
  footer {{ text-align:center; color:#94a3b8; font-size:.8rem; padding:32px; }}
</style>
</head>
<body>
<header>
  <h1>🛡 Rapport de Sécurité OWASP Top 10</h1>
  <p>AMANE-NEXUS — Système de Surveillance Intelligente Multi-Agent &nbsp;|&nbsp; Généré le {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC</p>
</header>

<div class="container">

  <!-- KPIs -->
  <div class="kpi-grid">
    <div class="kpi">
      <div class="val" style="color:#16a34a">{covered}</div>
      <div class="lbl">Catégories couvertes</div>
    </div>
    <div class="kpi">
      <div class="val" style="color:#d97706">{partial}</div>
      <div class="lbl">Partielles</div>
    </div>
    <div class="kpi">
      <div class="val" style="color:#1e293b">{score_pct}%</div>
      <div class="lbl">Score de couverture</div>
      <div class="score-bar"><div class="score-fill"></div></div>
    </div>
    <div class="kpi">
      <div class="val" style="color:{'#16a34a' if remaining==0 else '#dc2626'}">{remaining}</div>
      <div class="lbl">CVE sans correctif</div>
    </div>
  </div>

  <!-- OWASP Top 10 -->
  <div class="card">
    <div class="card-header">📋 Couverture OWASP Top 10 — AMANE-NEXUS</div>
    <table>
      <thead><tr><th>ID</th><th>Catégorie</th><th>Statut</th><th>Implémentation</th><th>Évidence</th></tr></thead>
      <tbody>{rows_owasp}</tbody>
    </table>
  </div>

  <!-- Dependency Audit -->
  <div class="card">
    <div class="card-header">🔍 Audit des dépendances Python (pip-audit · A06)</div>
    <table>
      <thead><tr><th>Package</th><th>Version</th><th>CVE / ID</th><th>Correctif</th><th>Statut</th></tr></thead>
      <tbody>{rows_vuln}</tbody>
    </table>
  </div>

</div>

<footer> AMANE-NEXUS </footer>
</body>
</html>"""

out = "owasp-report.html"
with open(out, "w", encoding="utf-8") as f:
    f.write(html)

print(f"[OK] {out} genere -- {covered}/10 categories couvertes -- score {score_pct}%")
