"""
Système de healthcheck pour Amadeus.
Permet de tester tous les sous-systèmes de l'application.
"""

import logging
import sys
import os
import json
from typing import Dict, Any, List
from datetime import datetime

# Configuration du logging pour le healthcheck
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("amadeus.healthcheck")

class AmadeusHealthCheck:
    """Classe principale pour effectuer les vérifications de santé."""
    
    def __init__(self):
        """Initialize the health check system."""
        self.results = {}
        self.errors = []
        self.warnings = []
        
    def check_all(self) -> Dict[str, Any]:
        """
        Effectue toutes les vérifications de santé.
        
        Returns:
            Dictionnaire complet des résultats
        """
        logger.info("Starting comprehensive Amadeus health check...")
        
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "unknown",
            "checks": {}
        }
        
        # Liste des vérifications à effectuer
        checks = [
            ("environment", self._check_environment),
            ("database", self._check_database),
            ("providers", self._check_providers),
            ("file_structure", self._check_file_structure),
            ("dependencies", self._check_dependencies),
            ("configuration", self._check_configuration)
        ]
        
        for check_name, check_func in checks:
            try:
                logger.info(f"Running {check_name} check...")
                result = check_func()
                self.results["checks"][check_name] = result
                logger.info(f"{check_name} check completed: {result.get('status', 'unknown')}")
            except Exception as e:
                logger.error(f"Error during {check_name} check: {e}")
                self.results["checks"][check_name] = {
                    "status": "error",
                    "error": str(e),
                    "details": {}
                }
        
        # Déterminer le statut global
        self._determine_overall_status()
        
        logger.info(f"Health check completed. Overall status: {self.results['overall_status']}")
        return self.results
    
    def _check_environment(self) -> Dict[str, Any]:
        """Vérification de l'environnement Python et des variables."""
        result = {"status": "healthy", "details": {}, "warnings": [], "errors": []}
        
        try:
            # Vérifier la version de Python
            python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
            result["details"]["python_version"] = python_version
            
            if sys.version_info < (3, 8):
                result["warnings"].append(f"Python version {python_version} is old. Recommended: 3.8+")
            
            # Vérifier les variables d'environnement importantes
            env_vars = ["HOME", "PATH", "PYTHONPATH"]
            for var in env_vars:
                result["details"][f"env_{var.lower()}"] = os.environ.get(var, "Not set")
            
            # Vérifier le répertoire de travail
            result["details"]["working_directory"] = os.getcwd()
            
            # Vérifier les permissions
            amadeus_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            result["details"]["amadeus_directory"] = amadeus_dir
            result["details"]["amadeus_readable"] = os.access(amadeus_dir, os.R_OK)
            result["details"]["amadeus_writable"] = os.access(amadeus_dir, os.W_OK)
            
        except Exception as e:
            result["status"] = "error"
            result["errors"].append(f"Environment check failed: {e}")
        
        if result["errors"]:
            result["status"] = "error"
        elif result["warnings"]:
            result["status"] = "warning"
        
        return result
    
    def _check_database(self) -> Dict[str, Any]:
        """Vérification de la base de données."""
        result = {"status": "healthy", "details": {}, "warnings": [], "errors": []}
        
        try:
            # Importer les modules de base de données
            from ..database.session import get_session, engine
            from ..database.models import Base, Provider, ProviderCredential, FineTuningJob
            
            result["details"]["database_url"] = str(engine.url)
            
            # Tester la connexion
            session = get_session()
            try:
                # Vérifier si les tables existent
                tables = engine.table_names()
                result["details"]["tables"] = tables
                
                expected_tables = ["providers", "provider_credentials", "fine_tuning_jobs"]
                missing_tables = [table for table in expected_tables if table not in tables]
                
                if missing_tables:
                    result["errors"].append(f"Missing database tables: {missing_tables}")
                
                # Compter les enregistrements
                provider_count = session.query(Provider).count()
                credential_count = session.query(ProviderCredential).count()
                job_count = session.query(FineTuningJob).count()
                
                result["details"]["record_counts"] = {
                    "providers": provider_count,
                    "credentials": credential_count,
                    "fine_tuning_jobs": job_count
                }
                
                logger.info(f"Database has {provider_count} providers, {credential_count} credentials, {job_count} jobs")
                
            finally:
                session.close()
        
        except ImportError as e:
            result["status"] = "error"
            result["errors"].append(f"Cannot import database modules: {e}")
        except Exception as e:
            result["status"] = "error"
            result["errors"].append(f"Database check failed: {e}")
        
        if result["errors"]:
            result["status"] = "error"
        elif result["warnings"]:
            result["status"] = "warning"
        
        return result
    
    def _check_providers(self) -> Dict[str, Any]:
        """Vérification du système de providers."""
        result = {"status": "healthy", "details": {}, "warnings": [], "errors": []}
        
        try:
            from .. import providers
            
            # Obtenir le statut de santé des providers
            health_status = providers.get_provider_health_status()
            result["details"]["provider_health"] = health_status
            
            # Vérifier les providers cloud
            cloud_providers = providers.get_cloud_providers()
            result["details"]["cloud_providers"] = {
                "count": len(cloud_providers),
                "providers": list(cloud_providers.keys())
            }
            
            # Vérifier les providers locaux
            local_providers = providers.get_local_providers()
            result["details"]["local_providers"] = {
                "count": len(local_providers),
                "providers": list(local_providers.keys())
            }
            
            # Vérifier le statut de la base de données
            db_status = providers.get_database_status()
            result["details"]["database_status"] = db_status
            
            # Analyser les problèmes
            if health_status.get("overall_status") == "error":
                result["status"] = "error"
                result["errors"].extend(health_status.get("errors", []))
            elif health_status.get("overall_status") == "warning":
                result["status"] = "warning"
                result["warnings"].extend(health_status.get("warnings", []))
            
            if len(cloud_providers) == 0:
                result["warnings"].append("No cloud providers discovered")
            
            if len(local_providers) == 0:
                result["warnings"].append("No local providers discovered")
        
        except Exception as e:
            result["status"] = "error"
            result["errors"].append(f"Provider system check failed: {e}")
        
        if result["errors"]:
            result["status"] = "error"
        elif result["warnings"]:
            result["status"] = "warning"
        
        return result
    
    def _check_file_structure(self) -> Dict[str, Any]:
        """Vérification de la structure des fichiers."""
        result = {"status": "healthy", "details": {}, "warnings": [], "errors": []}
        
        try:
            amadeus_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            result["details"]["amadeus_directory"] = amadeus_dir
            
            # Vérifier les répertoires importants
            important_dirs = [
                "providers",
                "providers/cloud",
                "providers/local",
                "database",
                "cli",
                "ui"
            ]
            
            existing_dirs = []
            missing_dirs = []
            
            for dir_path in important_dirs:
                full_path = os.path.join(amadeus_dir, dir_path)
                if os.path.exists(full_path):
                    existing_dirs.append(dir_path)
                else:
                    missing_dirs.append(dir_path)
            
            result["details"]["existing_directories"] = existing_dirs
            result["details"]["missing_directories"] = missing_dirs
            
            if missing_dirs:
                result["warnings"].append(f"Missing directories: {missing_dirs}")
            
            # Vérifier les providers spécifiques
            provider_dirs = {
                "cloud": ["openai", "ai_studio"],
                "local": []
            }
            
            for provider_type, expected_providers in provider_dirs.items():
                type_dir = os.path.join(amadeus_dir, "providers", provider_type)
                if os.path.exists(type_dir):
                    actual_providers = [
                        item for item in os.listdir(type_dir) 
                        if os.path.isdir(os.path.join(type_dir, item)) and not item.startswith('__')
                    ]
                    result["details"][f"{provider_type}_provider_dirs"] = actual_providers
                    
                    # Vérifier les fichiers essentiels pour chaque provider
                    for provider in actual_providers:
                        provider_path = os.path.join(type_dir, provider)
                        config_file = os.path.join(provider_path, "config.json")
                        provider_file = os.path.join(provider_path, "provider.py")
                        
                        if not os.path.exists(config_file):
                            result["warnings"].append(f"Missing config.json for {provider_type}.{provider}")
                        if not os.path.exists(provider_file):
                            result["warnings"].append(f"Missing provider.py for {provider_type}.{provider}")
        
        except Exception as e:
            result["status"] = "error"
            result["errors"].append(f"File structure check failed: {e}")
        
        if result["errors"]:
            result["status"] = "error"
        elif result["warnings"]:
            result["status"] = "warning"
        
        return result
    
    def _check_dependencies(self) -> Dict[str, Any]:
        """Vérification des dépendances Python."""
        result = {"status": "healthy", "details": {}, "warnings": [], "errors": []}
        
        # Dépendances critiques
        critical_deps = [
            "sqlalchemy",
            "requests",
            "logging"
        ]
        
        # Dépendances optionnelles
        optional_deps = [
            ("openai", "OpenAI provider"),
            ("google.generativeai", "Google AI Studio provider"),
            ("anthropic", "Anthropic provider"),
            ("streamlit", "Web UI"),
            ("click", "CLI interface")
        ]
        
        try:
            # Vérifier les dépendances critiques
            missing_critical = []
            for dep in critical_deps:
                try:
                    __import__(dep)
                    result["details"][f"critical_{dep}"] = "available"
                except ImportError:
                    missing_critical.append(dep)
                    result["details"][f"critical_{dep}"] = "missing"
            
            if missing_critical:
                result["errors"].append(f"Missing critical dependencies: {missing_critical}")
            
            # Vérifier les dépendances optionnelles
            available_optional = []
            missing_optional = []
            
            for dep, description in optional_deps:
                try:
                    __import__(dep)
                    available_optional.append((dep, description))
                    result["details"][f"optional_{dep.replace('.', '_')}"] = "available"
                except ImportError:
                    missing_optional.append((dep, description))
                    result["details"][f"optional_{dep.replace('.', '_')}"] = "missing"
            
            result["details"]["available_optional"] = available_optional
            result["details"]["missing_optional"] = missing_optional
            
            if missing_optional:
                missing_names = [f"{dep} ({desc})" for dep, desc in missing_optional]
                result["warnings"].append(f"Missing optional dependencies: {missing_names}")
        
        except Exception as e:
            result["status"] = "error"
            result["errors"].append(f"Dependency check failed: {e}")
        
        if result["errors"]:
            result["status"] = "error"
        elif result["warnings"]:
            result["status"] = "warning"
        
        return result
    
    def _check_configuration(self) -> Dict[str, Any]:
        """Vérification de la configuration générale."""
        result = {"status": "healthy", "details": {}, "warnings": [], "errors": []}
        
        try:
            # Vérifier les fichiers de configuration
            amadeus_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            config_files = [
                "config.json",
                "settings.py",
                ".env"
            ]
            
            for config_file in config_files:
                config_path = os.path.join(amadeus_dir, config_file)
                result["details"][f"config_{config_file.replace('.', '_')}"] = os.path.exists(config_path)
            
            # Vérifier les configurations des providers
            providers_dir = os.path.join(amadeus_dir, "providers")
            if os.path.exists(providers_dir):
                for provider_type in ["cloud", "local"]:
                    type_dir = os.path.join(providers_dir, provider_type)
                    if os.path.exists(type_dir):
                        provider_configs = []
                        for item in os.listdir(type_dir):
                            item_path = os.path.join(type_dir, item)
                            if os.path.isdir(item_path) and not item.startswith('__'):
                                config_file = os.path.join(item_path, "config.json")
                                if os.path.exists(config_file):
                                    try:
                                        with open(config_file, 'r') as f:
                                            config = json.load(f)
                                        provider_configs.append({
                                            "provider": item,
                                            "name": config.get("name", "Unknown"),
                                            "version": config.get("version", "Unknown"),
                                            "valid": True
                                        })
                                    except Exception as e:
                                        provider_configs.append({
                                            "provider": item,
                                            "valid": False,
                                            "error": str(e)
                                        })
                                        result["warnings"].append(f"Invalid config for {provider_type}.{item}: {e}")
                        
                        result["details"][f"{provider_type}_provider_configs"] = provider_configs
        
        except Exception as e:
            result["status"] = "error"
            result["errors"].append(f"Configuration check failed: {e}")
        
        if result["errors"]:
            result["status"] = "error"
        elif result["warnings"]:
            result["status"] = "warning"
        
        return result
    
    def _determine_overall_status(self):
        """Détermine le statut global basé sur tous les checks."""
        error_count = 0
        warning_count = 0
        
        for check_name, check_result in self.results["checks"].items():
            status = check_result.get("status", "unknown")
            if status == "error":
                error_count += 1
            elif status == "warning":
                warning_count += 1
        
        if error_count > 0:
            self.results["overall_status"] = "error"
        elif warning_count > 0:
            self.results["overall_status"] = "warning"
        else:
            self.results["overall_status"] = "healthy"
        
        self.results["summary"] = {
            "total_checks": len(self.results["checks"]),
            "errors": error_count,
            "warnings": warning_count,
            "healthy": len(self.results["checks"]) - error_count - warning_count
        }
    
    def print_summary(self):
        """Affiche un résumé des résultats."""
        print("\n" + "="*60)
        print("AMADEUS HEALTH CHECK SUMMARY")
        print("="*60)
        
        status_colors = {
            "healthy": "✅",
            "warning": "⚠️",
            "error": "❌",
            "unknown": "❓"
        }
        
        overall_status = self.results.get("overall_status", "unknown")
        print(f"Overall Status: {status_colors.get(overall_status, '❓')} {overall_status.upper()}")
        
        if "summary" in self.results:
            summary = self.results["summary"]
            print(f"Total Checks: {summary['total_checks']}")
            print(f"Healthy: {summary['healthy']}")
            print(f"Warnings: {summary['warnings']}")
            print(f"Errors: {summary['errors']}")
        
        print("\nDetailed Results:")
        print("-" * 60)
        
        for check_name, check_result in self.results.get("checks", {}).items():
            status = check_result.get("status", "unknown")
            emoji = status_colors.get(status, "❓")
            print(f"{emoji} {check_name.replace('_', ' ').title()}: {status}")
            
            # Afficher les erreurs et warnings
            if "errors" in check_result and check_result["errors"]:
                for error in check_result["errors"]:
                    print(f"   ❌ {error}")
            
            if "warnings" in check_result and check_result["warnings"]:
                for warning in check_result["warnings"]:
                    print(f"   ⚠️  {warning}")
        
        print("\n" + "="*60)


def main():
    """Point d'entrée principal pour le healthcheck CLI."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Amadeus Health Check System")
    parser.add_argument("--detailed", action="store_true", help="Show detailed results")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument("--check", choices=["environment", "database", "providers", "file_structure", "dependencies", "configuration"], help="Run specific check only")
    
    args = parser.parse_args()
    
    health_check = AmadeusHealthCheck()
    
    if args.check:
        # Exécuter un check spécifique
        check_methods = {
            "environment": health_check._check_environment,
            "database": health_check._check_database,
            "providers": health_check._check_providers,
            "file_structure": health_check._check_file_structure,
            "dependencies": health_check._check_dependencies,
            "configuration": health_check._check_configuration
        }
        
        result = check_methods[args.check]()
        
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"\n{args.check.replace('_', ' ').title()} Check Result:")
            print(f"Status: {result.get('status', 'unknown')}")
            if result.get('errors'):
                print("Errors:")
                for error in result['errors']:
                    print(f"  - {error}")
            if result.get('warnings'):
                print("Warnings:")
                for warning in result['warnings']:
                    print(f"  - {warning}")
    else:
        # Exécuter tous les checks
        results = health_check.check_all()
        
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            health_check.print_summary()
            
            if args.detailed:
                print("\nDetailed Information:")
                print("-" * 60)
                for check_name, check_result in results.get("checks", {}).items():
                    print(f"\n{check_name.replace('_', ' ').title()}:")
                    details = check_result.get("details", {})
                    for key, value in details.items():
                        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
