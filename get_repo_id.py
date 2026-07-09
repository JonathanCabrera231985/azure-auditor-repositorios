# get_repo_id.py

import argparse
import requests
import base64
import logging
import config

def _create_pat_auth_headers():
    """Creates base64 encoded authorization headers."""
    return {
        'Authorization': f'Basic {base64.b64encode(bytes(f":{config.AZURE_DEVOPS_PAT}", "ascii")).decode("ascii")}'
    }

def find_repository_id_by_name(repo_name):
    """
    Finds a repository's ID by its name within the configured project.
    """
    logging.info(f"Searching for repository with name: '{repo_name}'...")
    
    url = f"{config.AZURE_DEVOPS_INSTANCE}/{config.AZURE_DEVOPS_COLLECTION}/{config.AZURE_DEVOPS_PROJECT}/_apis/git/repositories?api-version=6.0"
    headers = _create_pat_auth_headers()
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        repositories = response.json().get('value', [])
        
        for repo in repositories:
            if repo.get('name').lower() == repo_name.lower():
                repo_id = repo.get('id')
                logging.info(f"SUCCESS: Found repository '{repo_name}' with ID: {repo_id}")
                return repo_id
                
        logging.warning(f"Repository '{repo_name}' not found in project '{config.AZURE_DEVOPS_PROJECT}'.")
        return None
        
    except requests.exceptions.RequestException as e:
        logging.error(f"An error occurred while fetching repositories: {e}")
        return None

def main():
    """
    Main function to find and print a repository ID.
    """
    parser = argparse.ArgumentParser(description="Find the ID of an Azure DevOps repository by its name.")
    parser.add_argument("repo_name", help="The name of the repository to find.")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level (default: INFO)."
    )
    args = parser.parse_args()

    # --- Setup Logging ---
    log_level = getattr(logging, args.log_level.upper())
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()]
    )
    # --- End Setup Logging ---

    try:
        repo_id = find_repository_id_by_name(args.repo_name)
        if repo_id:
            print(f"The ID for repository '{args.repo_name}' is: {repo_id}")
        else:
            print(f"Could not find the ID for repository '{args.repo_name}'. Check the log for details.")
            
    except Exception as e:
        logging.critical(f"A critical error occurred: {e}")

if __name__ == "__main__":
    main()
