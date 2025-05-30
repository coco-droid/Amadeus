"""
Template pour créer un nouveau provider Amadeus.

Ce fichier sert de guide pour créer de nouveaux providers.
Copiez ce template et adaptez-le selon vos besoins.
"""

from typing import Dict, List, Optional, Any
import logging

from amadeus.providers.base import Provider
from amadeus.providers.exceptions import ProviderError, ProviderConnectionError, ProviderAuthenticationError

class TemplateProvider(Provider):
    """
    Template de provider - remplacez cette description par celle de votre provider.
    
    Structure requise pour un nouveau provider:
    1. Hériter de la classe Provider
    2. Implémenter toutes les méthodes abstraites
    3. Créer un fichier config.json dans le même répertoire
    4. Placer le provider dans local/ ou cloud/ selon le type
    """
    
    def __init__(self, provider_id: str, config_path: Optional[str] = None):
        """
        Initialise le provider template.
        
        Args:
            provider_id: Identifiant du provider (ex: "cloud.template")
            config_path: Chemin vers la configuration (optionnel)
        """
        super().__init__(provider_id, config_path)
        self._connection = None
        
    def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        """
        Valide les informations d'identification pour ce provider.
        
        Args:
            credentials: Dictionnaire des informations d'identification
                        Les clés correspondent aux "key" dans auth_requirements
            
        Returns:
            True si les informations d'identification sont valides, False sinon
        """
        try:
            # Exemple de validation - adaptez selon vos besoins
            required_keys = [req.get("key") for req in self.auth_requirements if req.get("required", True)]
            
            for key in required_keys:
                if not credentials.get(key):
                    self.logger.error(f"Credential manquant: {key}")
                    return False
            
            # Ici, ajoutez votre logique de validation spécifique
            # Par exemple: tester une connexion, valider un format d'API key, etc.
            
            self.logger.info("Credentials validées avec succès")
            return True
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la validation des credentials: {e}")
            return False
    
    def get_connection(self, credentials: Dict[str, str]) -> Any:
        """
        Établit une connexion avec le provider en utilisant les informations d'identification.
        
        Args:
            credentials: Dictionnaire des informations d'identification
            
        Returns:
            Objet de connexion spécifique au provider (client API, session, etc.)
            
        Raises:
            ProviderConnectionError: En cas d'erreur de connexion
            ProviderAuthenticationError: En cas d'erreur d'authentification
        """
        return self.execute_with_error_handling(
            "get_connection",
            self._create_connection,
            credentials
        )
    
    def _create_connection(self, credentials: Dict[str, str]) -> Any:
        """
        Méthode interne pour créer la connexion.
        
        Args:
            credentials: Informations d'identification
            
        Returns:
            Objet de connexion
        """
        # Exemple d'implémentation - adaptez selon votre provider
        try:
            # Extraire les credentials nécessaires
            api_key = credentials.get("api_key")
            base_url = credentials.get("base_url", "https://api.example.com")
            
            # Créer votre client/connexion ici
            # Par exemple:
            # from your_provider_sdk import Client
            # connection = Client(api_key=api_key, base_url=base_url)
            
            # Pour ce template, on simule une connexion
            connection = {
                "api_key": api_key,
                "base_url": base_url,
                "connected": True
            }
            
            self._connection = connection
            self.logger.info("Connexion établie avec succès")
            return connection
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la création de la connexion: {e}")
            raise ProviderConnectionError(f"Impossible de se connecter: {str(e)}")
    
    def list_available_models(self, credentials: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        Liste les modèles disponibles pour ce provider.
        
        Args:
            credentials: Dictionnaire des informations d'identification
            
        Returns:
            Liste des modèles disponibles avec leurs métadonnées
            Format: [{"id": "model-id", "name": "Model Name", "type": "text", ...}, ...]
        """
        return self.execute_with_error_handling(
            "list_available_models",
            self._fetch_available_models,
            credentials
        )
    
    def _fetch_available_models(self, credentials: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        Méthode interne pour récupérer les modèles disponibles.
        
        Args:
            credentials: Informations d'identification
            
        Returns:
            Liste des modèles
        """
        # Obtenir une connexion
        connection = self.get_connection(credentials)
        
        try:
            # Ici, implémentez la logique pour récupérer les modèles
            # Par exemple: connection.list_models()
            
            # Pour ce template, on retourne les modèles par défaut de la config
            default_models = self.config.get("default_models", [])
            
            # Enrichir avec des informations dynamiques si nécessaire
            models = []
            for model in default_models:
                model_info = {
                    "id": model.get("id"),
                    "name": model.get("name"),
                    "type": model.get("type", "text"),
                    "provider": self.provider_id,
                    "description": model.get("description", ""),
                    "capabilities": model.get("capabilities", [])
                }
                models.append(model_info)
            
            self.logger.info(f"Récupéré {len(models)} modèles")
            return models
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la récupération des modèles: {e}")
            raise ProviderError(f"Impossible de récupérer les modèles: {str(e)}")
    
    def list_fine_tunable_models(self, credentials: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        Liste les modèles qui peuvent être fine-tunés sur ce provider.
        
        Args:
            credentials: Dictionnaire des informations d'identification
            
        Returns:
            Liste des modèles fine-tunables avec leurs métadonnées
        """
        return self.execute_with_error_handling(
            "list_fine_tunable_models",
            self._fetch_fine_tunable_models,
            credentials
        )
    
    def _fetch_fine_tunable_models(self, credentials: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        Méthode interne pour récupérer les modèles fine-tunables.
        
        Args:
            credentials: Informations d'identification
            
        Returns:
            Liste des modèles fine-tunables
        """
        # Obtenir tous les modèles disponibles
        all_models = self._fetch_available_models(credentials)
        
        # Filtrer ceux qui supportent le fine-tuning
        fine_tunable = []
        for model in all_models:
            capabilities = model.get("capabilities", [])
            if "fine_tuning" in capabilities or "fine-tuning" in capabilities:
                fine_tunable.append(model)
        
        self.logger.info(f"Trouvé {len(fine_tunable)} modèles fine-tunables")
        return fine_tunable
    
    def check_availability(self) -> bool:
        """
        Vérifie si le provider est actuellement disponible.
        
        Returns:
            True si le provider est disponible, False sinon
        """
        try:
            # Récupérer les credentials depuis le gestionnaire de config
            from ..core.config_manager import get_provider_config_manager
            
            config_manager = get_provider_config_manager()
            credentials = config_manager.get_provider_config(self.provider_id)
            
            if not credentials:
                self.logger.warning(f"Provider {self.provider_id} non configuré")
                self.is_available = False
                self._update_availability_in_db(False)
                return False
            
            # Tester la validité des credentials
            is_valid = self.validate_credentials(credentials)
            
            if is_valid:
                # Test de connexion rapide si possible
                try:
                    connection = self.get_connection(credentials)
                    # Ici, vous pourriez faire un test rapide (ping, list models, etc.)
                    self.logger.debug("Test de connexion réussi")
                except Exception as e:
                    self.logger.warning(f"Test de connexion échoué: {e}")
                    is_valid = False
            
            # Mettre à jour l'état
            self.is_available = is_valid
            self._update_availability_in_db(is_valid)
            
            return is_valid
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la vérification de disponibilité: {e}")
            self.is_available = False
            self._update_availability_in_db(False)
            return False

# Template de configuration (config.json)
TEMPLATE_CONFIG = {
    "name": "Template Provider",
    "version": "1.0.0",
    "description": "Template provider for demonstration",
    "provider_type": "cloud",  # ou "local"
    "auth_requirements": [
        {
            "key": "api_key",
            "name": "API Key",
            "description": "Your API key from the provider",
            "required": True,
            "secret": True
        },
        {
            "key": "base_url",
            "name": "Base URL",
            "description": "Base URL for the API (optional)",
            "required": False,
            "secret": False
        }
    ],
    "supported_features": {
        "text_generation": True,
        "chat": True,
        "fine_tuning": False,
        "embeddings": False,
        "image_generation": False
    },
    "default_models": [
        {
            "id": "template-model-1",
            "name": "Template Model 1",
            "type": "text",
            "description": "Example text generation model",
            "capabilities": ["text_generation", "chat"]
        }
    ]
}
