#!/bin/bash
# ===========================================================
# backup_sd.sh - Script de backup automatique de la carte SD
# ===========================================================
# UTILISATION :
#   1. Inserer une cle USB ou un disque externe
#   2. Lancer : sudo bash backup_sd.sh
#   3. Le script cree une image complete de la carte SD
#
# IMPORTANT : A faire AVANT la foire et garder la cle USB
# dans un sac separe du materiel principal.
#
# RESTAURATION :
#   sudo dd if=backup_plbd12_YYYYMMDD.img of=/dev/sdX bs=4M status=progress
#   (remplacer /dev/sdX par le device de la carte SD)
# ===========================================================

set -e

echo "========================================"
echo "  BACKUP CARTE SD - PLBD-12"
echo "========================================"
echo ""

# Verifier les privileges root
if [ "$EUID" -ne 0 ]; then
    echo "ERREUR: Ce script doit etre lance avec sudo"
    echo "Usage: sudo bash backup_sd.sh"
    exit 1
fi

# Date pour le nom du fichier
DATE=$(date +%Y%m%d_%H%M)
BACKUP_NAME="backup_plbd12_${DATE}.img"

# Trouver les supports USB montes
echo "Recherche de supports USB..."
USB_MOUNTS=$(lsblk -o NAME,MOUNTPOINT,SIZE,TYPE | grep -E "sd[a-z][0-9].*/" | grep -v "/$")
echo "$USB_MOUNTS"

if [ -z "$USB_MOUNTS" ]; then
    echo ""
    echo "ERREUR: Aucun support USB monte detecte."
    echo "Branchez une cle USB et reessayez."
    exit 1
fi

echo ""
read -p "Chemin de destination (ex: /media/pi/USB): " DEST_PATH

if [ ! -d "$DEST_PATH" ]; then
    echo "ERREUR: Le chemin $DEST_PATH n'existe pas."
    exit 1
fi

# Verifier l'espace disponible
ESPACE_DISPO=$(df -BG "$DEST_PATH" | awk 'NR==2{print $4}' | sed 's/G//')
TAILLE_SD=$(lsblk -b -o SIZE /dev/mmcblk0 | tail -1)
TAILLE_SD_GB=$((TAILLE_SD / 1073741824))

echo ""
echo "Taille carte SD:    ${TAILLE_SD_GB} Go"
echo "Espace disponible:  ${ESPACE_DISPO} Go"
echo "Fichier backup:     ${DEST_PATH}/${BACKUP_NAME}"

if [ "$ESPACE_DISPO" -lt "$TAILLE_SD_GB" ]; then
    echo ""
    echo "ERREUR: Espace insuffisant sur le support USB."
    exit 1
fi

echo ""
read -p "Demarrer le backup ? (o/n): " CONFIRM
if [ "$CONFIRM" != "o" ]; then
    echo "Backup annule."
    exit 0
fi

echo ""
echo "Backup en cours... (peut prendre 10-30 minutes)"
echo "NE PAS ETEINDRE LE RASPBERRY PI"
echo ""

# Backup avec dd + compression
dd if=/dev/mmcblk0 bs=4M status=progress | gzip > "${DEST_PATH}/${BACKUP_NAME}.gz"

echo ""
echo "========================================"
echo "  BACKUP TERMINE AVEC SUCCES"
echo "========================================"
echo "  Fichier: ${DEST_PATH}/${BACKUP_NAME}.gz"
echo "  Taille:  $(du -h "${DEST_PATH}/${BACKUP_NAME}.gz" | cut -f1)"
echo ""
echo "  RESTAURATION:"
echo "  gunzip -c ${BACKUP_NAME}.gz | sudo dd of=/dev/sdX bs=4M status=progress"
echo "========================================"
