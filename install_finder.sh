#!/usr/bin/env bash
# =============================================================================
#  FINDER v2.0 - Installeur Linux/macOS
#  by Data2391
# =============================================================================
set -euo pipefail

# --- Couleurs ---
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

step()  { echo -e "${CYAN}${BOLD}$*${NC}"; }
ok()    { echo -e "${GREEN}[OK] $*${NC}"; }
warn()  { echo -e "${YELLOW}[WARN] $*${NC}"; }
err()   { echo -e "${RED}${BOLD}[ERREUR] $*${NC}"; read -rp "Entree pour quitter..."; exit 1; }

clear
echo -e "${CYAN}${BOLD}"
echo "  =============================================="
echo "   FINDER v2.0 - Installeur Linux/macOS"
echo "   by Data2391"
echo "  =============================================="
echo -e "${NC}"

# --- Chemins ---
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FINDERDIR="$ROOT/finder"
SERVERPY="$FINDERDIR/server.py"
VENVDIR="$ROOT/venv"
VENVPY="$VENVDIR/bin/python"
VENVPIP="$VENVDIR/bin/pip"
VENVPW="$VENVDIR/bin/playwright"
LAUNCHER="$ROOT/lancer_finder.sh"

[[ -f "$SERVERPY" ]] || err "finder/server.py introuvable. Place ce script dans le dossier contenant finder/"
ok "Projet FINDER detecte."

# --- 1/8 Detection systeme ---
step "1/8 Detection du systeme..."
PKGMGR=""
for pm in pacman apt dnf zypper apk xbps-install brew; do
    command -v "$pm" &>/dev/null && PKGMGR="$pm" && break
done
PRIV=""
if [[ $EUID -eq 0 ]]; then PRIV=""
elif command -v sudo &>/dev/null; then PRIV="sudo"
elif command -v doas &>/dev/null; then PRIV="doas"
fi
ok "Gestionnaire: ${PKGMGR:-inconnu} | Privilege: ${PRIV:-root}"

# --- Fonction installation paquets ---
pkginstall() {
    case "$PKGMGR" in
        pacman)  $PRIV pacman -S --noconfirm --needed "$@" &>/dev/null || true ;;
        apt)     $PRIV apt-get install -y --no-install-recommends "$@" &>/dev/null || true ;;
        dnf)     $PRIV dnf install -y "$@" &>/dev/null || true ;;
        zypper)  $PRIV zypper install -y "$@" &>/dev/null || true ;;
        apk)     $PRIV apk add --no-cache "$@" &>/dev/null || true ;;
        brew)    brew install "$@" &>/dev/null || true ;;
        *)       warn "Gestionnaire $PKGMGR non gere." ;;
    esac
}

# --- 2/8 Python ---
step "2/8 Verification de Python 3.8+..."
PYTHON=""
for cmd in python3 python python3.12 python3.11 python3.10 python3.9 python3.8; do
    if command -v "$cmd" &>/dev/null; then
        MINOR=$("$cmd" -c "import sys;print(sys.version_info.minor)" 2>/dev/null || echo 0)
        MAJOR=$("$cmd" -c "import sys;print(sys.version_info.major)" 2>/dev/null || echo 0)
        if [[ $MAJOR -eq 3 && $MINOR -ge 8 ]]; then PYTHON="$cmd"; break; fi
    fi
done
[[ -n "$PYTHON" ]] || err "Python 3.8+ introuvable. Installe Python depuis https://python.org/downloads"
ok "Python: $($PYTHON --version)"

# --- 3/8 venv ---
step "3/8 Creation de l'environnement virtuel..."
if [[ -f "$VENVPY" ]]; then
    ok "Venv deja present."
else
    "$PYTHON" -m venv "$VENVDIR"
    [[ -f "$VENVPY" ]] || err "Impossible de creer le venv."
    ok "Venv cree: $VENVDIR"
fi

# --- 4/8 Flask + Playwright ---
step "4/8 Installation de Flask et Playwright..."
"$VENVPIP" install --upgrade pip --quiet
"$VENVPY" -c "import flask" &>/dev/null 2>&1 || "$VENVPIP" install flask --quiet
"$VENVPY" -c "import playwright" &>/dev/null 2>&1 || "$VENVPIP" install playwright --quiet
ok "Flask et Playwright prets."

# --- 5/8 Dependances systeme Playwright ---
step "5/8 Dependances systeme pour Playwright..."
"$VENVPW" install-deps chromium &>/dev/null 2>&1 || warn "install-deps non supporte, installation manuelle si necessaire."

# --- 6/8 Chromium ---
step "6/8 Installation de Chromium Playwright..."
PWCACHE="$HOME/.cache/ms-playwright"
CHROMIUMOK=false
[[ -n "$(find "$PWCACHE" -name 'chrome' -o -name 'chromium' -maxdepth 8 -type f -perm /111 2>/dev/null | head -1)" ]] && CHROMIUMOK=true
if "$CHROMIUMOK"; then
    ok "Playwright Chromium deja installe."
else
    warn "Telechargement Chromium... (150 MB)"
    "$VENVPW" install chromium
    ok "Chromium installe."
fi

# --- 7/8 Test ---
step "7/8 Test d'operabilite..."
IMPORTTEST=$("$VENVPY" -c "import flask,playwright,asyncio,json,re,urllib,threading,queue,uuid;print('ALLOK')" 2>/dev/null || echo "FAIL")
[[ "$IMPORTTEST" == "ALLOK" ]] && ok "Tous les modules sont operationnels." || warn "Probleme: $IMPORTTEST"

# --- 8/8 Lanceur ---
step "8/8 Creation du lanceur..."
cat > "$LAUNCHER" << 'LAUNCHEOF'
#!/usr/bin/env bash
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENVPY="$ROOT/venv/bin/python"
SERVER="$ROOT/finder/server.py"
[[ -f "$VENVPY" ]] || { echo "Venv absent. Relance install_finder.sh"; read -rp ""; exit 1; }
clear
printf '\033[0;36m\033[1m'
echo "  FINDER v2.0 - Data2391"
echo "  Serveur: http://localhost:8000"
echo "  NE PAS fermer ce terminal."
printf '\033[0m\n'
sleep 2
xdg-open http://localhost:8000 2>/dev/null || open http://localhost:8000 2>/dev/null || echo "Ouvre: http://localhost:8000"
"$VENVPY" "$SERVER"
LAUNCHEOF
chmod +x "$LAUNCHER"
ok "Lanceur cree: $LAUNCHER"

echo
echo -e "${GREEN}${BOLD}"
echo "  =============================================="
echo "   FINDER v2.0 EST PRET !"
echo "  =============================================="
echo -e "${NC}"
echo "  Lancer : ./lancer_finder.sh"
echo "  Interface : http://localhost:8000"
echo
read -rp "Lancer FINDER maintenant ? [o/N] " LAUNCHNOW
[[ "${LAUNCHNOW,,}" =~ ^(o|oui|y|yes)$ ]] && exec bash "$LAUNCHER"
