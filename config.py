# config.py

import os
from dotenv import load_dotenv

load_dotenv()

AZURE_DEVOPS_INSTANCE = os.getenv("AZURE_DEVOPS_INSTANCE")
AZURE_DEVOPS_COLLECTION = os.getenv("AZURE_DEVOPS_COLLECTION")
AZURE_DEVOPS_PROJECT = os.getenv("AZURE_DEVOPS_PROJECT")
AZURE_DEVOPS_REPOSITORY_NAME = os.getenv("AZURE_DEVOPS_REPOSITORY_NAME")
AZURE_DEVOPS_PAT = os.getenv("AZURE_DEVOPS_PAT")
LLM_API_KEY = os.getenv("LLM_API_KEY")

try:
    DAYS_TO_EXTRACT = int(os.getenv("DAYS_TO_EXTRACT", "1"))
except ValueError:
    DAYS_TO_EXTRACT = 1

if not all([AZURE_DEVOPS_INSTANCE, AZURE_DEVOPS_COLLECTION, AZURE_DEVOPS_PROJECT, AZURE_DEVOPS_REPOSITORY_NAME, AZURE_DEVOPS_PAT, LLM_API_KEY]):
    raise ValueError("One or more required environment variables are missing.")
