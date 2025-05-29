# 🎻 AMADEUS

**Assistant IA Avancé pour Fine-Tuning de Modèles**

Amadeus est votre compositeur d'IA personnel, conçu pour orchestrer et fine-tuner vos modèles d'intelligence artificielle avec élégance et précision.

## ✨ Fonctionnalités

- 🎼 **Interface CLI Moderne** - Interface utilisateur élégante et intuitive
- 🔧 **Fine-tuning Avancé** - Support pour LLMs, vLLM, génération d'images, synthèse vocale
- 🔮 **Oracle IA** - Assistant intelligent pour recommandations et diagnostics
- ⚙️ **Gestion des Providers** - Configuration simple des providers cloud et locaux
- 📊 **Préparation de Données** - Outils intégrés pour formater et valider vos datasets
- 🌐 **Multilingue** - Support complet français/anglais
- 📜 **Logging Avancé** - Système de logs sophistiqué avec visualisation

## 🚀 Installation

```bash
pip install amadeus-ai
```

## 💻 Utilisation

### Interface Utilisateur Interactive
```bash
amadeus
```

### Commandes CLI
```bash
# Gérer les providers
amadeus providers list
amadeus providers configure cloud.openai --interactive

# Visualiser les logs
amadeus view-logs --error --limit 50
amadeus view-logs --summary

# Gestion des modèles
amadeus models list --provider cloud.openai
```

## Configuration du Système

Les configurations sont stockées de manière sécurisée dans:
- `~/.amadeus/` - Dossier principal de configuration
- `~/.amadeus/amadeus.db` - Base de données SQLite pour les configurations
- `~/.amadeus/logs/` - Fichiers de logs rotatifs
- `~/.amadeus/language` - Préférence de langue

## 🎨 Interface Moderne

Amadeus propose une interface CLI moderne avec :
- **Thème sombre élégant** avec couleurs harmonieuses et contraste optimal
- **Navigation intuitive** avec raccourcis clavier et numérotation claire
- **Indicateur de sélection visuel** avec highlighting de l'option active
- **Affichage propre** sans interférence des logs (logs silencieux en arrière-plan)
- **Formulaires dynamiques** pour la configuration avec validation
- **Notifications visuelles** pour les actions et confirmations
- **Icônes et émojis** intégrés aux traductions pour une meilleure lisibilité
- **Interface responsive** qui s'adapte à la taille du terminal

## 🔧 Raccourcis Clavier

**Navigation générale :**
- `↑↓` ou `k/j` - Naviguer dans les menus
- `ENTER` ou `SPACE` - Sélectionner une option
- `ESC` - Retour au menu précédent
- `Q` - Quitter l'application
- `1-9` - Sélection rapide par numéro

**Dans les formulaires :**
- `TAB` - Champ suivant
- `SHIFT+TAB` - Champ précédent
- `ENTER` - Soumettre le formulaire
- `ESC` - Annuler et revenir

**Interface et affichage :**
- Interface claire avec highlighting visuel de l'option sélectionnée
- Les logs sont silencieux pendant l'utilisation de l'UI
- Utilisez `amadeus view-logs` pour consulter les logs
- `amadeus view-logs --summary` pour un résumé

## 🎯 Modes de Fine-tuning

- **LLMs Standard** - Fine-tuning classique pour modèles de langage
- **vLLM** - Optimisation haute performance
- **LoRA** - Low-Rank Adaptation pour un fine-tuning efficace
- **DPO** - Direct Preference Optimization
- **Génération d'images** - Modèles de diffusion
- **Synthèse vocale** - TTS et modèles audio

## Contribution

Les contributions sont les bienvenues! Consultez notre guide de contribution pour plus de détails.

## Licence

Ce projet est sous licence [MIT](LICENSE).
