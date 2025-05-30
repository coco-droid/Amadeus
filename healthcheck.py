#!/usr/bin/env python3
"""
Point d'entrée pour le système de healthcheck d'Amadeus.

Usage:
    python healthcheck.py                    # Check complet
    python healthcheck.py --detailed         # Check complet avec détails
    python healthcheck.py --json            # Sortie JSON
    python healthcheck.py --check providers # Check spécifique
"""

import sys
import os

# Ajouter le répertoire Amadeus au path Python
amadeus_dir = os.path.dirname(os.path.abspath(__file__))
if amadeus_dir not in sys.path:
    sys.path.insert(0, amadeus_dir)

try:
    from amadeus.cli.healthcheck import main
    
    if __name__ == "__main__":
        main()
        
except ImportError as e:
    print(f"❌ Erreur d'importation: {e}")
    print("Assurez-vous que tous les modules Amadeus sont correctement installés.")
    sys.exit(1)
except Exception as e:
    print(f"❌ Erreur lors de l'exécution du healthcheck: {e}")
    sys.exit(1)
