"""
Providers locaux pour Amadeus.

Ce package contient tous les providers qui fonctionnent localement,
comme unsloth pour le fine-tuning local.
"""

# Configuration d'un provider d'exemple pour les tests
CONFIG = {
    "name": "Local Test Provider",
    "version": "1.0.0",
    "description": "Provider de test local pour Amadeus",
    "provider_type": "local",
    "auth_requirements": [
        {
            "key": "model_path",
            "name": "Model Path",
            "description": "Chemin vers le modèle local",
            "required": True,
            "type": "string",
            "secret": False
        }
    ],
    "supported_features": {
        "text_generation": True,
        "embeddings": False,
        "fine_tuning": True
    },
    "default_models": [
        {
            "id": "local-test-model",
            "name": "Local Test Model",
            "type": "text"
        }
    ]
}

from amadeus.providers.base import Provider
from typing import Dict, List, Any

class LocalTestProvider(Provider):
    """Provider de test local."""
    
    def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        """Valide les credentials du provider."""
        return "model_path" in credentials and len(credentials["model_path"]) > 0
    
    def get_connection(self, credentials: Dict[str, str]) -> Any:
        """Établit une connexion avec le provider."""
        return {"status": "connected", "path": credentials.get("model_path")}
    
    def list_available_models(self, credentials: Dict[str, str]) -> List[Dict[str, Any]]:
        """Liste les modèles disponibles."""
        return self.default_models
    
    def list_fine_tunable_models(self, credentials: Dict[str, str]) -> List[Dict[str, Any]]:
        """Liste les modèles fine-tunables."""
        return self.default_models
