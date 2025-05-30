import abc
import argparse
import logging
from typing import Dict, List, Optional, Any, Callable
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from amadeus.i18n import get_translator
from amadeus.providers import registry, config_manager

console = Console()
logger = logging.getLogger("amadeus.commands")

class BaseCommand(abc.ABC):
    """Classe de base pour toutes les commandes Amadeus."""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.translator = get_translator()
    
    @abc.abstractmethod
    def add_arguments(self, parser: argparse.ArgumentParser):
        """Ajoute les arguments spécifiques à cette commande."""
        pass
    
    @abc.abstractmethod
    def execute(self, args: argparse.Namespace) -> int:
        """Exécute la commande. Retourne 0 en cas de succès, 1 en cas d'erreur."""
        pass
    
    def error(self, message: str):
        """Affiche un message d'erreur."""
        console.print(f"[bold red]Error:[/bold red] {message}")
    
    def success(self, message: str):
        """Affiche un message de succès."""
        console.print(f"[bold green]Success:[/bold green] {message}")
    
    def info(self, message: str):
        """Affiche un message d'information."""
        console.print(f"[blue]Info:[/blue] {message}")
    
    def warning(self, message: str):
        """Affiche un message d'avertissement."""
        console.print(f"[yellow]Warning:[/yellow] {message}")

class CommandRegistry:
    """Registre des commandes disponibles."""
    
    def __init__(self):
        self._commands: Dict[str, BaseCommand] = {}
        self._aliases: Dict[str, str] = {}
    
    def register(self, command: BaseCommand, aliases: Optional[List[str]] = None):
        """Enregistre une commande avec des alias optionnels."""
        self._commands[command.name] = command
        
        if aliases:
            for alias in aliases:
                self._aliases[alias] = command.name
        
        logger.debug(f"Commande enregistrée: {command.name}")
    
    def get_command(self, name: str) -> Optional[BaseCommand]:
        """Récupère une commande par son nom ou alias."""
        # Vérifier d'abord les alias
        if name in self._aliases:
            name = self._aliases[name]
        
        return self._commands.get(name)
    
    def list_commands(self) -> List[BaseCommand]:
        """Retourne la liste de toutes les commandes."""
        return list(self._commands.values())
    
    def get_command_names(self) -> List[str]:
        """Retourne la liste des noms de commandes."""
        return list(self._commands.keys())

# Instance globale du registre
command_registry = CommandRegistry()

class ProvidersCommand(BaseCommand):
    """Commandes pour gérer les providers."""
    
    def __init__(self):
        super().__init__("providers", "Manage AI providers configuration")
    
    def add_arguments(self, parser: argparse.ArgumentParser):
        subparsers = parser.add_subparsers(dest='action', help='Provider actions')
        
        # List providers
        list_parser = subparsers.add_parser('list', help='List available or configured providers')
        list_parser.add_argument('--type', choices=['cloud', 'local', 'all'], default='all',
                               help='Type of providers to list')
        list_parser.add_argument('--configured', action='store_true',
                               help='Show only configured providers')
        
        # Configure provider
        config_parser = subparsers.add_parser('configure', help='Configure a provider')
        config_parser.add_argument('provider_id', help='Provider ID to configure')
        config_parser.add_argument('--interactive', action='store_true',
                                 help='Interactive configuration mode')
        
        # Show provider details
        show_parser = subparsers.add_parser('show', help='Show provider details')
        show_parser.add_argument('provider_id', help='Provider ID to show')
        
        # Delete provider configuration
        delete_parser = subparsers.add_parser('delete', help='Delete provider configuration')
        delete_parser.add_argument('provider_id', help='Provider ID to delete')
        delete_parser.add_argument('--force', action='store_true',
                                 help='Force deletion without confirmation')
    
    def execute(self, args: argparse.Namespace) -> int:
        try:
            if args.action == 'list':
                return self._list_providers(args)
            elif args.action == 'configure':
                return self._configure_provider(args)
            elif args.action == 'show':
                return self._show_provider(args)
            elif args.action == 'delete':
                return self._delete_provider(args)
            else:
                self.error("No action specified. Use --help for usage information.")
                return 1
        except Exception as e:
            self.error(f"Command failed: {str(e)}")
            logger.exception("Command execution failed")
            return 1
    
    def _list_providers(self, args: argparse.Namespace) -> int:
        """Liste les providers disponibles ou configurés."""
        try:
            if args.configured:
                # Lister les providers configurés en utilisant la nouvelle interface
                from amadeus.providers import get_all_providers
                all_providers = get_all_providers()
                configured_providers = {k: v for k, v in all_providers.items() if v.get('is_configured', False)}
                
                if not configured_providers:
                    self.info("No providers configured.")
                    return 0
                
                table = Table(title="Configured Providers")
                table.add_column("Provider ID", style="cyan")
                table.add_column("Name", style="green")
                table.add_column("Type", style="yellow")
                table.add_column("Status", style="magenta")
                
                for provider_id, config in configured_providers.items():
                    name = config.get('name', provider_id)
                    # Utiliser provider_type de façon cohérente
                    provider_type = config.get('provider_type', config.get('type', 'unknown'))
                    is_available = config.get('is_available', False)
                    status = "Available" if is_available else "Unavailable"
                    table.add_row(provider_id, name, provider_type, status)
                
                console.print(table)
            else:
                # Lister les providers disponibles
                from amadeus.providers import get_all_providers
                all_providers = get_all_providers()
                
                if args.type != 'all':
                    all_providers = {k: v for k, v in all_providers.items() 
                                   if v.get('provider_type', v.get('type')) == args.type}
                
                if not all_providers:
                    self.info(f"No {args.type} providers available.")
                    return 0
                
                table = Table(title=f"Available {args.type.title()} Providers")
                table.add_column("Provider ID", style="cyan")
                table.add_column("Name", style="green")
                table.add_column("Description", style="white")
                table.add_column("Version", style="yellow")
                table.add_column("Configured", style="magenta")
                
                for provider_id, config in all_providers.items():
                    name = config.get('name', provider_id)
                    description = config.get('description', 'No description')
                    version = config.get('version', 'Unknown')
                    is_configured = config.get('is_configured', False)
                    configured = "Yes" if is_configured else "No"
                    
                    table.add_row(provider_id, name, description, version, configured)
                
                console.print(table)
            
            return 0
            
        except Exception as e:
            self.error(f"Failed to list providers: {str(e)}")
            logger.exception("Error listing providers")
            return 1
    
    def _configure_provider(self, args: argparse.Namespace) -> int:
        """Configure un provider."""
        try:
            provider_id = args.provider_id
            
            # Vérifier que le provider existe
            try:
                provider_config = registry.get_provider_config(provider_id)
            except Exception:
                self.error(f"Provider '{provider_id}' not found.")
                return 1
            
            provider_name = provider_config.get('name', provider_id)
            auth_requirements = provider_config.get('auth_requirements', [])
            
            if not auth_requirements:
                self.info(f"Provider '{provider_name}' does not require configuration.")
                return 0
            
            self.info(f"Configuring provider: {provider_name}")
            
            # Mode interactif ou récupération des valeurs existantes
            if args.interactive:
                credentials = {}
                
                for req in auth_requirements:
                    key = req.get('key', '')
                    name = req.get('name', key)
                    description = req.get('description', '')
                    is_secret = req.get('secret', True)
                    is_required = req.get('required', True)
                    
                    # Afficher la description si disponible
                    if description:
                        console.print(f"[blue]{name}:[/blue] {description}")
                    
                    # Demander la valeur
                    prompt = f"Enter {name}"
                    if not is_required:
                        prompt += " (optional)"
                    prompt += ": "
                    
                    if is_secret:
                        import getpass
                        value = getpass.getpass(prompt)
                    else:
                        value = input(prompt)
                    
                    if value or not is_required:
                        credentials[key] = value
                    elif is_required:
                        self.error(f"Field '{name}' is required.")
                        return 1
                
                # Sauvegarder la configuration
                config_manager.save_provider_config(provider_id, credentials)
                self.success(f"Provider '{provider_name}' configured successfully.")
                return 0
            else:
                # Mode non-interactif - afficher les champs requis
                self.info(f"Provider '{provider_name}' requires the following configuration:")
                
                for req in auth_requirements:
                    name = req.get('name', req.get('key', ''))
                    description = req.get('description', '')
                    is_required = req.get('required', True)
                    status = "Required" if is_required else "Optional"
                    
                    console.print(f"  • [cyan]{name}[/cyan] ({status})")
                    if description:
                        console.print(f"    {description}")
                
                self.info("Use --interactive flag to configure interactively.")
                return 0
                
        except Exception as e:
            self.error(f"Failed to configure provider: {str(e)}")
            return 1
    
    def _show_provider(self, args: argparse.Namespace) -> int:
        """Affiche les détails d'un provider."""
        try:
            provider_id = args.provider_id
            
            # Récupérer la configuration
            try:
                config = registry.get_provider_config(provider_id)
            except Exception:
                self.error(f"Provider '{provider_id}' not found.")
                return 1
            
            # Vérifier s'il est configuré
            is_configured = config_manager.check_provider_configured(provider_id)
            
            # Afficher les informations
            panel_content = []
            panel_content.append(f"[bold]Name:[/bold] {config.get('name', provider_id)}")
            panel_content.append(f"[bold]Type:[/bold] {config.get('provider_type', 'Unknown')}")
            panel_content.append(f"[bold]Version:[/bold] {config.get('version', 'Unknown')}")
            panel_content.append(f"[bold]Description:[/bold] {config.get('description', 'No description')}")
            panel_content.append(f"[bold]Configured:[/bold] {'Yes' if is_configured else 'No'}")
            panel_content.append(f"[bold]Available:[/bold] {'Yes' if registry.is_provider_available(provider_id) else 'No'}")
            
            # Fonctionnalités supportées
            features = config.get('supported_features', {})
            if features:
                panel_content.append("\n[bold]Supported Features:[/bold]")
                for feature, value in features.items():
                    if isinstance(value, bool):
                        status = "✓" if value else "✗"
                        panel_content.append(f"  • {feature}: {status}")
                    elif isinstance(value, list):
                        panel_content.append(f"  • {feature}: {', '.join(value)}")
                    else:
                        panel_content.append(f"  • {feature}: {value}")
            
            # Modèles par défaut
            models = config.get('default_models', [])
            if models:
                panel_content.append("\n[bold]Default Models:[/bold]")
                for model in models:
                    model_name = model.get('name', model.get('id', 'Unknown'))
                    panel_content.append(f"  • {model_name}")
            
            console.print(Panel("\n".join(panel_content), title=f"Provider: {provider_id}"))
            return 0
            
        except Exception as e:
            self.error(f"Failed to show provider details: {str(e)}")
            return 1
    
    def _delete_provider(self, args: argparse.Namespace) -> int:
        """Supprime la configuration d'un provider."""
        try:
            provider_id = args.provider_id
            
            # Vérifier que le provider est configuré
            if not config_manager.check_provider_configured(provider_id):
                self.warning(f"Provider '{provider_id}' is not configured.")
                return 0
            
            # Demander confirmation si pas forcé
            if not args.force:
                try:
                    provider_config = registry.get_provider_config(provider_id)
                    provider_name = provider_config.get('name', provider_id)
                except:
                    provider_name = provider_id
                
                response = input(f"Are you sure you want to delete configuration for '{provider_name}'? [y/N]: ")
                if response.lower() not in ['y', 'yes']:
                    self.info("Operation cancelled.")
                    return 0
            
            # Supprimer la configuration
            success = config_manager.delete_provider_config(provider_id)
            
            if success:
                self.success(f"Provider '{provider_id}' configuration deleted successfully.")
                return 0
            else:
                self.error(f"Failed to delete provider '{provider_id}' configuration.")
                return 1
                
        except Exception as e:
            self.error(f"Failed to delete provider configuration: {str(e)}")
            return 1

class ModelsCommand(BaseCommand):
    """Commandes pour gérer les modèles."""
    
    def __init__(self):
        super().__init__("models", "Manage AI models")
    
    def add_arguments(self, parser: argparse.ArgumentParser):
        subparsers = parser.add_subparsers(dest='action', help='Model actions')
        
        # List models
        list_parser = subparsers.add_parser('list', help='List available models')
        list_parser.add_argument('--provider', help='Filter by provider')
        list_parser.add_argument('--type', help='Filter by model type')
        
        # Show model details
        show_parser = subparsers.add_parser('show', help='Show model details')
        show_parser.add_argument('model_id', help='Model ID to show')
        
        # Test model
        test_parser = subparsers.add_parser('test', help='Test a model')
        test_parser.add_argument('model_id', help='Model ID to test')
        test_parser.add_argument('--prompt', default="Hello, how are you?", help='Test prompt')
    
    def execute(self, args: argparse.Namespace) -> int:
        try:
            if args.action == 'list':
                return self._list_models(args)
            elif args.action == 'show':
                return self._show_model(args)
            elif args.action == 'test':
                return self._test_model(args)
            else:
                self.error("No action specified. Use --help for usage information.")
                return 1
        except Exception as e:
            self.error(f"Command failed: {str(e)}")
            logger.exception("Command execution failed")
            return 1
    
    def _list_models(self, args: argparse.Namespace) -> int:
        """Liste les modèles disponibles."""
        self.info("Models management not fully implemented yet.")
        
        # Placeholder - afficher les modèles par défaut des providers
        all_providers = registry.get_all_providers()
        
        table = Table(title="Available Models")
        table.add_column("Model ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Provider", style="yellow")
        table.add_column("Type", style="magenta")
        
        for provider_id, config in all_providers.items():
            if args.provider and provider_id != args.provider:
                continue
                
            models = config.get('default_models', [])
            for model in models:
                model_id = model.get('id', 'unknown')
                model_name = model.get('name', model_id)
                model_type = model.get('type', 'unknown')
                
                if args.type and model_type != args.type:
                    continue
                    
                table.add_row(model_id, model_name, provider_id, model_type)
        
        console.print(table)
        return 0
    
    def _show_model(self, args: argparse.Namespace) -> int:
        """Affiche les détails d'un modèle."""
        self.info(f"Model details for '{args.model_id}' not implemented yet.")
        return 0
    
    def _test_model(self, args: argparse.Namespace) -> int:
        """Teste un modèle."""
        self.info(f"Testing model '{args.model_id}' with prompt: '{args.prompt}'")
        self.info("Model testing not implemented yet.")
        return 0

class TrainingCommand(BaseCommand):
    """Commandes pour l'entraînement des modèles."""
    
    def __init__(self):
        super().__init__("training", "Manage model training and fine-tuning")
    
    def add_arguments(self, parser: argparse.ArgumentParser):
        subparsers = parser.add_subparsers(dest='action', help='Training actions')
        
        # Start training
        start_parser = subparsers.add_parser('start', help='Start model training')
        start_parser.add_argument('--type', choices=['llm', 'vllm', 'image', 'tts', 'audio'],
                                required=True, help='Type of model to train')
        start_parser.add_argument('--config', help='Training configuration file')
        start_parser.add_argument('--dataset', help='Training dataset path')
        
        # List training jobs
        list_parser = subparsers.add_parser('list', help='List training jobs')
        list_parser.add_argument('--status', choices=['running', 'completed', 'failed', 'all'],
                               default='all', help='Filter by status')
        
        # Show training status
        status_parser = subparsers.add_parser('status', help='Show training job status')
        status_parser.add_argument('job_id', help='Training job ID')
        
        # Stop training
        stop_parser = subparsers.add_parser('stop', help='Stop training job')
        stop_parser.add_argument('job_id', help='Training job ID')
    
    def execute(self, args: argparse.Namespace) -> int:
        try:
            if args.action == 'start':
                return self._start_training(args)
            elif args.action == 'list':
                return self._list_training_jobs(args)
            elif args.action == 'status':
                return self._show_training_status(args)
            elif args.action == 'stop':
                return self._stop_training(args)
            else:
                self.error("No action specified. Use --help for usage information.")
                return 1
        except Exception as e:
            self.error(f"Command failed: {str(e)}")
            logger.exception("Command execution failed")
            return 1
    
    def _start_training(self, args: argparse.Namespace) -> int:
        """Démarre un entraînement."""
        self.info(f"Starting {args.type} training...")
        if args.config:
            self.info(f"Using config: {args.config}")
        if args.dataset:
            self.info(f"Using dataset: {args.dataset}")
        
        self.info("Training functionality not implemented yet.")
        return 0
    
    def _list_training_jobs(self, args: argparse.Namespace) -> int:
        """Liste les tâches d'entraînement."""
        self.info(f"Listing training jobs with status: {args.status}")
        self.info("Training jobs management not implemented yet.")
        return 0
    
    def _show_training_status(self, args: argparse.Namespace) -> int:
        """Affiche le statut d'un entraînement."""
        self.info(f"Showing status for training job: {args.job_id}")
        self.info("Training status not implemented yet.")
        return 0
    
    def _stop_training(self, args: argparse.Namespace) -> int:
        """Arrête un entraînement."""
        self.info(f"Stopping training job: {args.job_id}")
        self.info("Training stop not implemented yet.")
        return 0

# Enregistrer les commandes
command_registry.register(ProvidersCommand(), aliases=['provider', 'p'])
command_registry.register(ModelsCommand(), aliases=['model', 'm'])
command_registry.register(TrainingCommand(), aliases=['train', 't'])

def get_command_registry() -> CommandRegistry:
    """Retourne l'instance du registre de commandes."""
    return command_registry
