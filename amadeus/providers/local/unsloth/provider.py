from typing import Dict, List, Any
from amadeus.providers.base import Provider
from amadeus.providers.exceptions import ProviderConnectionError, ProviderAuthenticationError

class UnslothProvider(Provider):
    """
    Provider pour Unsloth - Fine-tuning local ultra rapide.
    """
    
    def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        """
        Valide les informations d'identification Unsloth.
        Pour un provider local, on vérifie principalement l'installation.
        """
        try:
            import unsloth
            return True
        except ImportError:
            return False
    
    def get_connection(self, credentials: Dict[str, str]) -> Any:
        """
        Établit une connexion avec Unsloth.
        """
        try:
            import unsloth
            return unsloth
        except ImportError:
            raise ProviderConnectionError("Unsloth n'est pas installé. Installez-le avec 'pip install unsloth'.")
    
    def list_available_models(self, credentials: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        Liste les modèles disponibles pour Unsloth.
        """
        try:
            # Modèles supportés par Unsloth
            return [
                {
                    "id": "unsloth/llama-2-7b-bnb-4bit",
                    "name": "Llama 2 7B (4-bit)",
                    "description": "Llama 2 7B optimisé avec quantization 4-bit"
                },
                {
                    "id": "unsloth/mistral-7b-v0.1-bnb-4bit", 
                    "name": "Mistral 7B (4-bit)",
                    "description": "Mistral 7B optimisé avec quantization 4-bit"
                }
            ]
        except Exception as e:
            raise ProviderConnectionError(f"Erreur lors de la récupération des modèles Unsloth: {str(e)}")
    
    def list_fine_tunable_models(self, credentials: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        Liste les modèles qui peuvent être fine-tunés avec Unsloth.
        """
        return self.list_available_models(credentials)
