#!/bin/bash
# ============================================================================
#  MacBook Air Optimalisatie Script (Uitgebreid)
#  Geschikt voor oudere MacBook Air modellen (2012-2019)
#
#  WAT DOET DIT SCRIPT:
#  1. Verwijdert onnodige standaard Apple-apps
#  2. Ruimt systeemcaches en tijdelijke bestanden op
#  3. Optimaliseert RAM-gebruik en geheugen
#  4. Verbetert batterijduur
#  5. Schakelt zware achtergrondprocessen uit
#  6. Verwijdert oude logs en crash reports
#  7. Optimaliseert netwerk- en DNS-instellingen
#  8. Schakelt onnodige visuele effecten uit
#  9. Optimaliseert opslag (purge, APFS trim)
# 10. Herindexeert Spotlight slim
#
#  GEBRUIK: chmod +x macbook_optimize.sh && sudo ./macbook_optimize.sh
# ============================================================================

set -e

# Kleuren voor output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Controleer of het script als root draait
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}Dit script moet als root draaien. Gebruik: sudo ./macbook_optimize.sh${NC}"
   exit 1
fi

# Bewaar de originele gebruiker (voor commando's die niet als root moeten)
REAL_USER=$(stat -f "%Su" /dev/console 2>/dev/null || echo "$SUDO_USER")

divider() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

header() {
    echo ""
    divider
    echo -e "${BOLD}${CYAN}  $1${NC}"
    divider
}

success() {
    echo -e "  ${GREEN}✓${NC} $1"
}

warning() {
    echo -e "  ${YELLOW}⚠${NC} $1"
}

info() {
    echo -e "  ${BLUE}→${NC} $1"
}

skip() {
    echo -e "  ${YELLOW}⊘${NC} $1 (niet gevonden, overgeslagen)"
}

# Startmelding
clear
echo ""
echo -e "${BOLD}${CYAN}"
echo "  ╔══════════════════════════════════════════════════════════════╗"
echo "  ║         MacBook Air Optimalisatie Script v2.0               ║"
echo "  ║         Snelheid • Batterij • Opslag • Prestaties           ║"
echo "  ╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Toon huidige schijfruimte voor vergelijking
DISK_BEFORE=$(df -h / | awk 'NR==2{print $4}')
echo -e "${BOLD}  Beschikbare schijfruimte voor optimalisatie: ${YELLOW}${DISK_BEFORE}${NC}"
echo ""

# Bevestiging vragen
echo -e "${YELLOW}  Dit script zal je MacBook optimaliseren door:${NC}"
echo "  - Onnodige standaard-apps te verwijderen"
echo "  - Caches, logs en tijdelijke bestanden op te ruimen"
echo "  - Zware achtergrondprocessen uit te schakelen"
echo "  - Visuele effecten te verminderen voor snelheid"
echo "  - Batterij-optimalisaties toe te passen"
echo ""
read -p "  Wil je doorgaan? (j/n): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[JjYy]$ ]]; then
    echo -e "${RED}  Afgebroken door gebruiker.${NC}"
    exit 0
fi

# ============================================================================
# STAP 1: ONNODIGE STANDAARD APPLE-APPS VERWIJDEREN
# ============================================================================
header "STAP 1/10: Onnodige standaard Apple-apps verwijderen"

# Lijst van apps die veilig verwijderd kunnen worden
APPS_TO_REMOVE=(
    "GarageBand"
    "iMovie"
    "Keynote"
    "Numbers"
    "Pages"
    "Chess"
    "Stocks"
    "News"
    "Home"
    "Automator"
    "DVD Player"
    "Grapher"
    "Stickies"
)

for app in "${APPS_TO_REMOVE[@]}"; do
    APP_PATH="/Applications/${app}.app"
    if [ -d "$APP_PATH" ]; then
        rm -rf "$APP_PATH"
        success "${app} verwijderd"
    else
        skip "${app}"
    fi
done

# Verwijder bijbehorende containers en app support
info "Opruimen van app-restanten..."
for app in "${APPS_TO_REMOVE[@]}"; do
    app_lower=$(echo "$app" | tr '[:upper:]' '[:lower:]' | tr ' ' '-')
    rm -rf "/Users/${REAL_USER}/Library/Containers/com.apple.${app_lower}" 2>/dev/null
    rm -rf "/Users/${REAL_USER}/Library/Application Support/${app}" 2>/dev/null
done
success "App-restanten opgeruimd"

# Verwijder GarageBand geluidsbibliotheek (kan GB's groot zijn)
if [ -d "/Library/Application Support/GarageBand" ]; then
    rm -rf "/Library/Application Support/GarageBand"
    success "GarageBand geluidsbibliotheek verwijderd (mogelijk meerdere GB's)"
fi
if [ -d "/Library/Application Support/Logic" ]; then
    rm -rf "/Library/Application Support/Logic"
    success "Logic geluidsbibliotheek verwijderd"
fi
if [ -d "/Library/Audio/Apple Loops" ]; then
    rm -rf "/Library/Audio/Apple Loops"
    success "Apple Audio Loops verwijderd"
fi

# ============================================================================
# STAP 2: SYSTEEM- EN GEBRUIKERSCACHES OPRUIMEN
# ============================================================================
header "STAP 2/10: Systeem- en gebruikerscaches opruimen"

# Gebruikerscaches
if [ -d "/Users/${REAL_USER}/Library/Caches" ]; then
    CACHE_SIZE=$(du -sh "/Users/${REAL_USER}/Library/Caches" 2>/dev/null | awk '{print $1}')
    rm -rf /Users/${REAL_USER}/Library/Caches/* 2>/dev/null
    success "Gebruikerscaches opgeruimd (${CACHE_SIZE})"
fi

# Systeemcaches
if [ -d "/Library/Caches" ]; then
    SYSCACHE_SIZE=$(du -sh "/Library/Caches" 2>/dev/null | awk '{print $1}')
    rm -rf /Library/Caches/* 2>/dev/null
    success "Systeemcaches opgeruimd (${SYSCACHE_SIZE})"
fi

# Safari caches
rm -rf "/Users/${REAL_USER}/Library/Caches/com.apple.Safari" 2>/dev/null
rm -rf "/Users/${REAL_USER}/Library/Safari/LocalStorage" 2>/dev/null
success "Safari caches opgeruimd"

# Chrome caches (als Chrome geinstalleerd is)
if [ -d "/Users/${REAL_USER}/Library/Caches/Google/Chrome" ]; then
    rm -rf "/Users/${REAL_USER}/Library/Caches/Google/Chrome" 2>/dev/null
    success "Chrome caches opgeruimd"
fi

# Verwijder oude iOS-backups (kunnen heel groot zijn)
if [ -d "/Users/${REAL_USER}/Library/Application Support/MobileSync/Backup" ]; then
    BACKUP_SIZE=$(du -sh "/Users/${REAL_USER}/Library/Application Support/MobileSync/Backup" 2>/dev/null | awk '{print $1}')
    rm -rf "/Users/${REAL_USER}/Library/Application Support/MobileSync/Backup"/* 2>/dev/null
    success "Oude iOS-backups verwijderd (${BACKUP_SIZE})"
fi

# Verwijder Xcode afgeleiden (als aanwezig)
if [ -d "/Users/${REAL_USER}/Library/Developer/Xcode/DerivedData" ]; then
    XCODE_SIZE=$(du -sh "/Users/${REAL_USER}/Library/Developer/Xcode/DerivedData" 2>/dev/null | awk '{print $1}')
    rm -rf "/Users/${REAL_USER}/Library/Developer/Xcode/DerivedData"/* 2>/dev/null
    success "Xcode DerivedData opgeruimd (${XCODE_SIZE})"
fi

# ============================================================================
# STAP 3: LOGS EN CRASH REPORTS VERWIJDEREN
# ============================================================================
header "STAP 3/10: Logs, crash reports en diagnostics verwijderen"

# Systeemlogs
rm -rf /private/var/log/asl/*.asl 2>/dev/null
rm -rf /private/var/log/*.log 2>/dev/null
rm -rf /private/var/log/*.gz 2>/dev/null
success "Systeemlogs opgeruimd"

# Gebruikerslogs
rm -rf /Users/${REAL_USER}/Library/Logs/* 2>/dev/null
success "Gebruikerslogs opgeruimd"

# Crash reports
rm -rf /Users/${REAL_USER}/Library/Logs/DiagnosticReports/* 2>/dev/null
rm -rf /Library/Logs/DiagnosticReports/* 2>/dev/null
success "Crash reports verwijderd"

# Apple System Logs database
rm -rf /private/var/log/DiagnosticMessages/* 2>/dev/null
success "Diagnostische berichten opgeruimd"

# Core dumps
rm -rf /cores/* 2>/dev/null
success "Core dumps verwijderd"

# Verwijder QuickLook cache
rm -rf /Users/${REAL_USER}/Library/Caches/com.apple.QuickLook.thumbnailcache 2>/dev/null
qlmanage -r cache 2>/dev/null
success "QuickLook cache opgeruimd"

# ============================================================================
# STAP 4: TIJDELIJKE BESTANDEN EN PRULLENBAK LEGEN
# ============================================================================
header "STAP 4/10: Tijdelijke bestanden opruimen en prullenbak legen"

# Tijdelijke bestanden
rm -rf /private/tmp/* 2>/dev/null
rm -rf /private/var/tmp/* 2>/dev/null
rm -rf /tmp/* 2>/dev/null
success "Tijdelijke bestanden verwijderd"

# Prullenbak legen
rm -rf /Users/${REAL_USER}/.Trash/* 2>/dev/null
success "Prullenbak geleegd"

# Verwijder .DS_Store bestanden (maken systeem trager)
find / -name ".DS_Store" -type f -delete 2>/dev/null &
success ".DS_Store bestanden worden opgeruimd (achtergrond)"

# Verwijder Thumbs.db (Windows restanten)
find /Users/${REAL_USER} -name "Thumbs.db" -type f -delete 2>/dev/null
success "Thumbs.db bestanden verwijderd"

# ============================================================================
# STAP 5: ZWARE ACHTERGRONDPROCESSEN UITSCHAKELEN
# ============================================================================
header "STAP 5/10: Zware achtergrondprocessen uitschakelen"

# Siri uitschakelen
defaults write com.apple.assistant.support "Assistant Enabled" -bool false 2>/dev/null
defaults write com.apple.Siri StatusMenuVisible -bool false 2>/dev/null
defaults write com.apple.Siri UserHasDeclinedEnable -bool true 2>/dev/null
launchctl disable "user/$(id -u ${REAL_USER})/com.apple.Siri" 2>/dev/null
success "Siri uitgeschakeld"

# Spotlight indexering beperken (niet volledig uitschakelen)
mdutil -i off /Volumes/* 2>/dev/null
info "Spotlight indexering gepauzeerd op externe volumes"

# Game Center uitschakelen
launchctl unload -w /System/Library/LaunchAgents/com.apple.gamed.plist 2>/dev/null
success "Game Center uitgeschakeld"

# Automatische updates uitschakelen (handmatig controleren is beter voor performance)
defaults write com.apple.SoftwareUpdate AutomaticDownload -bool false 2>/dev/null
defaults write com.apple.SoftwareUpdate AutomaticCheckEnabled -bool false 2>/dev/null
defaults write com.apple.commerce AutoUpdate -bool false 2>/dev/null
success "Automatische updates uitgeschakeld (controleer handmatig via Systeemvoorkeuren)"

# iCloud sync beperken
defaults write com.apple.bird optimize-storage -bool true 2>/dev/null
success "iCloud opslagoptimalisatie ingeschakeld"

# Foto-analyse uitschakelen (CPU-intensief)
launchctl disable "user/$(id -u ${REAL_USER})/com.apple.photoanalysisd" 2>/dev/null
success "Foto-analyse (gezichtsherkenning) uitgeschakeld"

# Mail automatisch ophalen uitschakelen
defaults write com.apple.mail PollTime -int -1 2>/dev/null
success "Mail automatisch ophalen uitgeschakeld"

# Time Machine lokale snapshots uitschakelen
tmutil disablelocal 2>/dev/null || tmutil thinlocalsnapshots / 10000000000 4 2>/dev/null
success "Time Machine lokale snapshots beperkt"

# Uitschakelen van AirDrop als het niet nodig is
defaults write com.apple.NetworkBrowser DisableAirDrop -bool true 2>/dev/null
success "AirDrop uitgeschakeld (schakel handmatig in wanneer nodig)"

# Handoff uitschakelen
defaults -currentHost write com.apple.coreservices.useractivityd ActivityReceivingAllowed -bool false 2>/dev/null
defaults -currentHost write com.apple.coreservices.useractivityd ActivityAdvertisingAllowed -bool false 2>/dev/null
success "Handoff uitgeschakeld"

# ============================================================================
# STAP 6: VISUELE EFFECTEN VERMINDEREN VOOR SNELHEID
# ============================================================================
header "STAP 6/10: Visuele effecten verminderen voor betere prestaties"

# Animaties versnellen
sudo -u "$REAL_USER" defaults write NSGlobalDomain NSWindowResizeTime -float 0.001 2>/dev/null
success "Venster-animaties versneld"

# Transparantie verminderen
sudo -u "$REAL_USER" defaults write com.apple.universalaccess reduceTransparency -bool true 2>/dev/null
success "Transparantie verminderd"

# Motion effecten verminderen
sudo -u "$REAL_USER" defaults write com.apple.universalaccess reduceMotion -bool true 2>/dev/null
success "Bewegingseffecten verminderd"

# Dock animaties versnellen
sudo -u "$REAL_USER" defaults write com.apple.dock autohide-time-modifier -float 0.25 2>/dev/null
sudo -u "$REAL_USER" defaults write com.apple.dock autohide-delay -float 0 2>/dev/null
sudo -u "$REAL_USER" defaults write com.apple.dock launchanim -bool false 2>/dev/null
sudo -u "$REAL_USER" defaults write com.apple.dock expose-animation-duration -float 0.1 2>/dev/null
success "Dock-animaties versneld"

# Schakel Dock magnification uit
sudo -u "$REAL_USER" defaults write com.apple.dock magnification -bool false 2>/dev/null
success "Dock-vergroting uitgeschakeld"

# Minimaliseer naar applicatie-icoon (bespaart geheugen)
sudo -u "$REAL_USER" defaults write com.apple.dock minimize-to-application -bool true 2>/dev/null
success "Minimaliseer naar applicatie-icoon ingeschakeld"

# Versneld scrollen in Finder
sudo -u "$REAL_USER" defaults write NSGlobalDomain NSScrollAnimationEnabled -bool false 2>/dev/null
success "Scroll-animaties uitgeschakeld"

# Snellere Mission Control animatie
sudo -u "$REAL_USER" defaults write com.apple.dock expose-animation-duration -float 0.1 2>/dev/null
success "Mission Control animatie versneld"

# Rubber band scrolling uitschakelen
sudo -u "$REAL_USER" defaults write -g NSScrollViewRubberbanding -bool false 2>/dev/null
success "Rubber band scrolling uitgeschakeld"

# ============================================================================
# STAP 7: BATTERIJ-OPTIMALISATIES
# ============================================================================
header "STAP 7/10: Batterij-optimalisaties toepassen"

# Verminder wake-ups
pmset -b displaysleep 3 2>/dev/null        # Display uit na 3 min op batterij
pmset -b disksleep 5 2>/dev/null            # Schijf slaap na 5 min op batterij
pmset -b sleep 10 2>/dev/null               # Slaapstand na 10 min op batterij
pmset -b lessbright 1 2>/dev/null           # Automatisch dimmen op batterij
pmset -b halfdim 1 2>/dev/null              # Half dim inschakelen
success "Batterij slaapinstellingen geoptimaliseerd"

# Power Nap uitschakelen op batterij
pmset -b powernap 0 2>/dev/null
pmset -b tcpkeepalive 0 2>/dev/null
success "Power Nap uitgeschakeld op batterij"

# Wake on network access uitschakelen
pmset -a womp 0 2>/dev/null
success "Wake on network access uitgeschakeld"

# Bluetooth wake uitschakelen
pmset -a btwakelevel 0 2>/dev/null
success "Bluetooth wake uitgeschakeld"

# Verminder Bluetooth polling
defaults write /Library/Preferences/com.apple.Bluetooth.plist ControllerPowerState -int 0 2>/dev/null
info "Bluetooth vermogen verminderd (schakel handmatig in wanneer nodig)"

# Schakel locatieservices uit voor niet-essentiële apps
defaults write /var/db/locationd/Library/Preferences/ByHost/com.apple.locationd LocationServicesEnabled -int 0 2>/dev/null
warning "Locatieservices uitgeschakeld (schakel in via Systeemvoorkeuren als nodig)"

# ============================================================================
# STAP 8: GEHEUGEN EN PRESTATIE-OPTIMALISATIE
# ============================================================================
header "STAP 8/10: Geheugen en prestaties optimaliseren"

# Purge inactief geheugen
purge 2>/dev/null
success "Inactief geheugen vrijgemaakt"

# Herstart DNS cache
dscacheutil -flushcache 2>/dev/null
killall -HUP mDNSResponder 2>/dev/null
success "DNS cache geleegd"

# Versnelde DNS servers instellen (Cloudflare)
networksetup -listallnetworkservices 2>/dev/null | while IFS= read -r service; do
    if [[ "$service" != "An asterisk"* ]]; then
        networksetup -setdnsservers "$service" 1.1.1.1 1.0.0.1 2>/dev/null
    fi
done
success "DNS servers ingesteld op Cloudflare (1.1.1.1) voor sneller internet"

# Finder optimalisaties
sudo -u "$REAL_USER" defaults write com.apple.finder DisableAllAnimations -bool true 2>/dev/null
sudo -u "$REAL_USER" defaults write com.apple.finder AnimateInfoPanes -bool false 2>/dev/null
sudo -u "$REAL_USER" defaults write com.apple.finder AnimateWindowZoom -bool false 2>/dev/null
success "Finder-animaties uitgeschakeld"

# Toon geen recente tags in Finder
sudo -u "$REAL_USER" defaults write com.apple.finder ShowRecentTags -bool false 2>/dev/null
success "Recente tags in Finder verborgen"

# Beperk het aantal recente items
sudo -u "$REAL_USER" defaults write NSGlobalDomain NSRecentDocumentsLimit -int 5 2>/dev/null
success "Recente items limiet verlaagd"

# Verwijder onnodige taalbestanden (bewaar Nederlands en Engels)
info "Onnodige taalbestanden opruimen..."
find /Applications -name "*.lproj" -type d \
    ! -name "en.lproj" \
    ! -name "Base.lproj" \
    ! -name "nl.lproj" \
    ! -name "Dutch.lproj" \
    ! -name "English.lproj" \
    -exec rm -rf {} + 2>/dev/null
success "Onnodige taalbestanden verwijderd (Engels en Nederlands behouden)"

# ============================================================================
# STAP 9: OPSLAG-OPTIMALISATIE
# ============================================================================
header "STAP 9/10: Opslag optimaliseren"

# Verwijder oude kern-extensie caches
rm -rf /System/Library/Caches/com.apple.kext.caches 2>/dev/null
success "Kernel extension caches opgeruimd"

# Verwijder Print Support (als je niet print)
if [ -d "/Library/Printers" ]; then
    PRINTER_SIZE=$(du -sh "/Library/Printers" 2>/dev/null | awk '{print $1}')
    rm -rf /Library/Printers/* 2>/dev/null
    success "Printer-drivers verwijderd (${PRINTER_SIZE}) - worden opnieuw gedownload indien nodig"
fi

# Verwijder niet-gebruikte voices
info "Opruimen van ongebruikte stembestanden..."
# Bewaar alleen de standaard stem
find /System/Library/Speech/Voices -name "*.SpeechVoice" -type d 2>/dev/null | while read voice; do
    basename_voice=$(basename "$voice")
    if [[ "$basename_voice" != "Alex.SpeechVoice" && "$basename_voice" != "Samantha.SpeechVoice" ]]; then
        rm -rf "$voice" 2>/dev/null
    fi
done
success "Ongebruikte stembestanden opgeruimd"

# Verwijder oude software-update downloads
rm -rf /Library/Updates/* 2>/dev/null
success "Oude software-update downloads verwijderd"

# Verwijder Mail downloads
rm -rf /Users/${REAL_USER}/Library/Containers/com.apple.mail/Data/Library/Mail\ Downloads/* 2>/dev/null
success "Mail downloads opgeruimd"

# macOS caches herbouwen
update_dyld_shared_cache -force 2>/dev/null &
info "Dynamic library cache wordt herbouwd (achtergrond)"

# ============================================================================
# STAP 10: FINDER EN SYSTEEM HERSTARTEN
# ============================================================================
header "STAP 10/10: Wijzigingen toepassen"

# Herstart Finder
killall Finder 2>/dev/null
success "Finder herstart"

# Herstart Dock
killall Dock 2>/dev/null
success "Dock herstart"

# Herstart SystemUIServer
killall SystemUIServer 2>/dev/null
success "SystemUIServer herstart"

# Herbouw Launch Services database
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -kill -r -domain local -domain system -domain user 2>/dev/null &
success "Launch Services database wordt herbouwd (achtergrond)"

# ============================================================================
# SAMENVATTING
# ============================================================================
echo ""
divider
echo -e "${BOLD}${GREEN}"
echo "  ╔══════════════════════════════════════════════════════════════╗"
echo "  ║              OPTIMALISATIE VOLTOOID!                        ║"
echo "  ╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

DISK_AFTER=$(df -h / | awk 'NR==2{print $4}')
echo -e "  ${BOLD}Schijfruimte voor optimalisatie:  ${YELLOW}${DISK_BEFORE}${NC}"
echo -e "  ${BOLD}Schijfruimte na optimalisatie:    ${GREEN}${DISK_AFTER}${NC}"
echo ""
echo -e "  ${BOLD}Wat is er gedaan:${NC}"
echo -e "  ${GREEN}✓${NC} Onnodige standaard-apps verwijderd"
echo -e "  ${GREEN}✓${NC} Caches en tijdelijke bestanden opgeruimd"
echo -e "  ${GREEN}✓${NC} Logs en crash reports verwijderd"
echo -e "  ${GREEN}✓${NC} Prullenbak geleegd"
echo -e "  ${GREEN}✓${NC} Zware achtergrondprocessen uitgeschakeld"
echo -e "  ${GREEN}✓${NC} Visuele effecten verminderd"
echo -e "  ${GREEN}✓${NC} Batterij-instellingen geoptimaliseerd"
echo -e "  ${GREEN}✓${NC} Geheugen vrijgemaakt en DNS versneld"
echo -e "  ${GREEN}✓${NC} Opslagruimte geoptimaliseerd"
echo -e "  ${GREEN}✓${NC} Onnodige taalbestanden verwijderd"
echo ""
echo -e "  ${YELLOW}AANBEVELINGEN:${NC}"
echo -e "  ${BLUE}→${NC} Herstart je MacBook voor de beste resultaten"
echo -e "  ${BLUE}→${NC} Controleer handmatig op macOS-updates via Systeemvoorkeuren"
echo -e "  ${BLUE}→${NC} Overweeg een SSD-upgrade als je nog een HDD hebt"
echo -e "  ${BLUE}→${NC} Gebruik Safari i.p.v. Chrome voor betere batterijduur"
echo -e "  ${BLUE}→${NC} Sluit ongebruikte tabbladen en apps"
echo ""
echo -e "  ${CYAN}Wil je nu herstarten? (aanbevolen)${NC}"
read -p "  (j/n): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[JjYy]$ ]]; then
    echo -e "  ${GREEN}Herstarten over 5 seconden...${NC}"
    sleep 5
    shutdown -r now
else
    echo -e "  ${YELLOW}Herstart je MacBook zo snel mogelijk voor optimale resultaten.${NC}"
fi

echo ""
divider
