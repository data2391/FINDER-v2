# FINDER v2.0 — Sonar OSINT Local

## Structure
```
finder/
├── server.py           ← Flask server (port 8000)
├── scraper.py          ← Playwright scraper (Google Dorks + Whitepages)
├── requirements.txt
├── templates/
│   └── index.html      ← Interface principale
└── static/
    ├── style.css
    └── script.js
```

## Installation

```bash
cd finder
pip install -r requirements.txt
playwright install chromium
```

## Lancement

```bash
python server.py
```
Ouvre ensuite → http://localhost:8000

## Utilisation
- **Nom Prénom** : extraction civile complète
- **Pseudo** : liaison avatar numérique → identité réelle
- **Nom d'entreprise** : cartographie de réseau

## Boutons
| Bouton | Fonction |
|--------|----------|
| 👁 | Masquer/afficher un groupe de résultats |
| ▼ Tout voir | Déplier les résultats complets du groupe |
| ❓ Comment ça fonctionne | Ouvre la FAQ OSINT |

## Dorks générés automatiquement
- `site:linkedin.com/in/ "Cible"`
- `site:instagram.com "Cible"`
- `site:facebook.com "Cible"`
- `site:twitter.com "Cible" OR site:x.com "Cible"`
- `site:vk.com "Cible"`
- Recherche images Google
- Whitepages.fr scraping via Playwright

## Notes
- Google peut imposer un CAPTCHA après de nombreuses requêtes. Relancez après quelques minutes.
- Toutes les données restent locales, aucun envoi externe.