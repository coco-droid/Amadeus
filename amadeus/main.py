import argparse
import sys
import os
from typing import Optional

from amadeus.core.ui import AmadeusApp
from amadeus.core.logging import setup_logging, get_log_viewer
from amadeus.i18n import get_translator, set_language
from amadeus.core.ui.handlers.commands import get_command_registry

import typer
from rich.console import Console
from rich.panel import Panel
import logging

app = typer.Typer(help="Assistant de Fine-Tuning pour Modèles d'IA Générative")
console = Console()

# Fichier pour stocker la langue préférée
CONFIG_DIR = os.path.expanduser("~/.amadeus")
LANG_FILE = os.path.join(CONFIG_DIR, "language")

def get_saved_language():
    """Récupère la langue sauvegardée si elle existe."""
    try:
        if os.path.exists(LANG_FILE):
            with open(LANG_FILE, 'r') as f:
                return f.read().strip()
        return None
    except:
        return None

def save_language_preference(lang_code):
    """Sauvegarde la langue préférée."""
    try:
        if not os.path.exists(CONFIG_DIR):
            os.makedirs(CONFIG_DIR)
        with open(LANG_FILE, 'w') as f:
            f.write(lang_code)
    except:
        pass

def view_logs_command(args):
    """Commande pour visualiser les logs."""
    from amadeus.core.logging import LogManager
    
    log_manager = LogManager()
    log_viewer = get_log_viewer(log_manager)
    
    # Afficher le résumé si demandé
    if args.summary:
        log_viewer.display_summary()
        return
    
    # Paramètres de filtrage
    level_filter = None
    if args.error:
        level_filter = 'ERROR'
    elif args.warning:
        level_filter = 'WARNING'
    elif args.info:
        level_filter = 'INFO'
    elif args.debug:
        level_filter = 'DEBUG'
    elif args.critical:
        level_filter = 'CRITICAL'
    elif args.level:
        level_filter = args.level.upper()
    
    # Filtrer et afficher les logs
    logs = log_manager.filter_logs(
        level_filter=level_filter,
        logger_filter=args.logger,
        date_filter=args.date,
        limit=args.limit,
        search=args.search
    )
    
    log_viewer.display_logs(logs, colorize=not args.no_color)

def cleanup_logs_command(args):
    """Commande pour nettoyer les anciens logs."""
    from amadeus.core.logging import LogManager
    
    log_manager = LogManager()
    
    print(f"Nettoyage des logs plus anciens que {args.days} jours...")
    log_manager.cleanup_old_logs(args.days)
    print("Nettoyage terminé.")

def create_main_parser():
    """Crée le parser principal avec toutes les commandes."""
    parser = argparse.ArgumentParser(
        prog='amadeus',
        description="Amadeus - Assistant de Fine-Tuning pour Modèles d'IA Générative",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Options globales
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Mode verbose avec logs détaillés')
    parser.add_argument('--language', '--lang', '-l', type=str,
                       help='Langue (en, fr)')
    parser.add_argument('--no-ui', action='store_true',
                       help='Mode ligne de commande uniquement')
    
    # Sous-commandes
    subparsers = parser.add_subparsers(dest='command', help='Commandes disponibles')
    
    # Commande run (par défaut) - interface utilisateur
    run_parser = subparsers.add_parser('run', help='Lancer l\'interface utilisateur')
    run_parser.add_argument('--reset', action='store_true',
                           help='Réinitialiser les préférences')
    
    # Commandes de gestion des logs
    logs_parser = subparsers.add_parser('view-logs', help='Visualiser les logs')
    logs_parser.add_argument('--error', action='store_true', help='Afficher uniquement les erreurs')
    logs_parser.add_argument('--warning', action='store_true', help='Afficher uniquement les warnings')
    logs_parser.add_argument('--info', action='store_true', help='Afficher uniquement les infos')
    logs_parser.add_argument('--debug', action='store_true', help='Afficher uniquement les debug')
    logs_parser.add_argument('--critical', action='store_true', help='Afficher uniquement les critiques')
    logs_parser.add_argument('--level', type=str, help='Filtrer par niveau spécifique')
    logs_parser.add_argument('--logger', type=str, help='Filtrer par nom de logger')
    logs_parser.add_argument('--date', type=str, help='Filtrer par date (YYYY-MM-DD)')
    logs_parser.add_argument('--search', type=str, help='Rechercher un terme dans les messages')
    logs_parser.add_argument('--limit', type=int, default=100, help='Nombre maximum de lignes (défaut: 100)')
    logs_parser.add_argument('--no-color', action='store_true', help='Désactiver la colorisation')
    logs_parser.add_argument('--summary', action='store_true', help='Afficher un résumé des logs')
    logs_parser.set_defaults(func=view_logs_command)
    
    cleanup_parser = subparsers.add_parser('cleanup-logs', help='Nettoyer les anciens logs')
    cleanup_parser.add_argument('--days', type=int, default=30, 
                               help='Garder les logs des N derniers jours (défaut: 30)')
    cleanup_parser.set_defaults(func=cleanup_logs_command)
    
    # Ajouter les commandes du registre
    command_registry = get_command_registry()
    for command in command_registry.list_commands():
        cmd_parser = subparsers.add_parser(command.name, help=command.description)
        command.add_arguments(cmd_parser)
        cmd_parser.set_defaults(command_obj=command)
    
    return parser

def run_ui_app(verbose=False, language=None, reset=False):
    """Lance l'application UI sans logs intrusifs."""
    # Configuration du logging (plus silencieux pour l'UI)
    if not verbose:
        # Réduire le niveau de logging pour l'interface UI
        logging.getLogger().setLevel(logging.WARNING)
        
    log_manager = setup_logging()
    
    logger = logging.getLogger("amadeus.cli")
    logger.info("Démarrage d'Amadeus")
    
    # Réinitialiser les préférences si demandé
    if reset and os.path.exists(LANG_FILE):
        os.remove(LANG_FILE)
    
    # Déterminer la langue à utiliser
    saved_lang = None if reset else get_saved_language()
    lang_to_use = language or saved_lang
    first_run = lang_to_use is None
    
    logger.info(f"Premier lancement: {first_run}")
    logger.info(f"Langue sauvegardée: {saved_lang}")
    
    # Définir la langue si spécifiée
    if lang_to_use:
        success = set_language(lang_to_use)
        if success:
            save_language_preference(lang_to_use)
            logger.info(f"Langue définie sur: {lang_to_use}")
        else:
            logger.warning(f"Impossible de définir la langue: {lang_to_use}")
    
    translator = get_translator()
    
    if verbose:
        console.print("[bold green]Démarrage d'Amadeus en mode verbose...[/bold green]")
    
    try:
        # Lancer l'application interactive
        amadeus_app = AmadeusApp(first_run=first_run)
        amadeus_app.run()
        
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Opération annulée par l'utilisateur.[/bold yellow]")
    except Exception as e:
        console.print(f"[bold red]Erreur: {str(e)}[/bold red]")
        if verbose:
            console.print_exception()
    finally:
        goodbye_msg = translator.get("goodbye_message", "Merci d'avoir utilisé Amadeus!")
        console.print(Panel(goodbye_msg, title="Au revoir"))

def run_command_mode(args):
    """Exécute une commande en mode CLI."""
    # Configuration basique du logging pour les commandes CLI
    setup_logging()
    
    # Définir la langue si spécifiée
    if args.language:
        set_language(args.language)
    elif not args.no_ui:
        # Charger la langue sauvegardée si disponible
        saved_lang = get_saved_language()
        if saved_lang:
            set_language(saved_lang)
    
    # Exécuter la commande
    if hasattr(args, 'command_obj'):
        # Commande du registre
        try:
            exit_code = args.command_obj.execute(args)
            sys.exit(exit_code)
        except Exception as e:
            console.print(f"[bold red]Error executing command:[/bold red] {str(e)}")
            if args.verbose:
                console.print_exception()
            sys.exit(1)
    elif hasattr(args, 'func'):
        # Commande avec fonction définie
        try:
            args.func(args)
        except Exception as e:
            console.print(f"[bold red]Error executing command:[/bold red] {str(e)}")
            if args.verbose:
                console.print_exception()
            sys.exit(1)
    else:
        console.print("[bold red]Error:[/bold red] Unknown command")
        sys.exit(1)

def main():
    """Point d'entrée principal."""
    parser = create_main_parser()
    
    # Si aucun argument n'est fourni, lancer l'UI
    if len(sys.argv) == 1:
        run_ui_app()
        return
    
    args = parser.parse_args()
    
    # Si la commande est 'run' ou pas de commande spécifiée, lancer l'UI
    if args.command is None or args.command == 'run':
        run_ui_app(
            verbose=args.verbose,
            language=args.language,
            reset=getattr(args, 'reset', False)
        )
    else:
        # Mode commande CLI
        run_command_mode(args)

if __name__ == "__main__":
    main()