from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="amadeus",
    version="0.1.0",
    author="Amadeus Team",
    author_email="team@amadeus.ai",
    description="Assistant de Fine-Tuning pour Modèles d'IA Générative",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/amadeus-ai/amadeus",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.8",
    install_requires=[
        "prompt-toolkit>=3.0.0",
        "pygments>=2.10.0",
        "rich>=12.0.0",
        "pyyaml>=6.0",
        "typer>=0.9.0",
        "requests>=2.25.0",
        "cryptography>=3.4.0",  # Pour le chiffrement des credentials
    ],
    extras_require={
        "openai": ["openai>=1.0.0"],
        "google": ["google-generativeai"],
        "unsloth": ["unsloth[cu118]"],  # Ou autre variante selon la config GPU
        "anthropic": ["anthropic>=0.3.0"],
        "huggingface": ["huggingface_hub>=0.16.0", "transformers>=4.30.0"],
        "all": [
            "openai>=1.0.0",
            "google-generativeai",
            "unsloth",
            "huggingface_hub>=0.16.0",
            "transformers>=4.30.0",
            "anthropic>=0.3.0"
        ]
    },
    entry_points={
        'console_scripts': [
            'amadeus=amadeus.cli:main',
        ],
    },
    include_package_data=True,
    package_data={
        'amadeus': [
            'i18n/*.json',
            'i18n/*/*.json',
            'providers/configs/*.yaml',
            'providers/configs/*.json',
        ],
    },
    zip_safe=False,
)
