# azure_devops.py

import requests
import base64
import difflib
import logging
from datetime import datetime, timedelta
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
import config
import os

def _create_pat_auth_headers():
    """Creates base64 encoded authorization headers."""
    return {
        'Authorization': f'Basic {base64.b64encode(bytes(f":{config.AZURE_DEVOPS_PAT}", "ascii")).decode("ascii")}'
    }

def get_recent_commits(start_date=None):
    """
    Fetches commits from an Azure DevOps repository since a given start date.
    If no start date is provided, defaults to the last DAYS_TO_EXTRACT days.
    """
    if start_date:
        from_date = start_date
        logging.info(f"Fetching commits from {from_date} to now...")
    else:
        days = getattr(config, "DAYS_TO_EXTRACT", 1)
        from_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
        logging.info(f"Fetching commits from the last {days} day(s)...")

    url = f"{config.AZURE_DEVOPS_INSTANCE}/{config.AZURE_DEVOPS_COLLECTION}/{config.AZURE_DEVOPS_PROJECT}/_apis/git/repositories/{config.AZURE_DEVOPS_REPOSITORY_NAME}/commits"
    
    params = {
        'searchCriteria.fromDate': from_date,
        'api-version': '6.0'
    }
    
    headers = _create_pat_auth_headers()
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        commits = data.get('value', [])
        logging.info(f"Found {len(commits)} commits in the specified period.")

        enriched_commits = []
        for commit in commits:
            enriched_commit = get_commit_with_work_items(commit['commitId'])
            enriched_commits.append(enriched_commit)
        
        return enriched_commits
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching commits: {e}")
        return []

def get_work_item_details(work_item_url):
    """Fetches details for a single work item."""
    headers = _create_pat_auth_headers()
    try:
        response = requests.get(work_item_url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching work item details from {work_item_url}: {e}")
        return None

def get_commit_with_work_items(commit_id):
    """
    Fetches a single commit and enriches it with details of associated work items.
    """
    url = f"{config.AZURE_DEVOPS_INSTANCE}/{config.AZURE_DEVOPS_COLLECTION}/{config.AZURE_DEVOPS_PROJECT}/_apis/git/repositories/{config.AZURE_DEVOPS_REPOSITORY_NAME}/commits/{commit_id}?api-version=6.0"
    headers = _create_pat_auth_headers()
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        commit_details = response.json()
        
        work_item_urls = [wi['url'] for wi in commit_details.get('workItems', [])]
        
        if work_item_urls:
            logging.info(f"Commit {commit_id[:8]} is linked to {len(work_item_urls)} work item(s). Fetching details...")
            work_items_details = []
            for url in work_item_urls:
                details = get_work_item_details(url)
                if details:
                    work_items_details.append(details)
            commit_details['workItemsDetails'] = work_items_details
        else:
            commit_details['workItemsDetails'] = []

        return commit_details
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching commit details for {commit_id}: {e}")
        return None


def _get_item_content(file_path, commit_id):
    """
    Fetches the raw content of a file at a specific commit using the Items API.
    """
    if not file_path or not commit_id:
        return ""

    url = f"{config.AZURE_DEVOPS_INSTANCE}/{config.AZURE_DEVOPS_COLLECTION}/{config.AZURE_DEVOPS_PROJECT}/_apis/git/repositories/{config.AZURE_DEVOPS_REPOSITORY_NAME}/items?path={file_path}&versionType=Commit&version={commit_id}&api-version=6.0&download=true"
    headers = _create_pat_auth_headers()
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.text 
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching item content for {file_path} in commit {commit_id[:8]} from {url}: {e}")
        return ""

def _create_valid_filename(commit_id, commit_date_str, extension):
    """Creates a valid filename from commit info."""
    import re
    short_commit_id = commit_id[:12]
    date_part = commit_date_str.split('T')[0]
    filename = f"{short_commit_id}_{date_part}.{extension}"
    return re.sub(r'[^a-zA-Z0-9_\-\.]', '_', filename)


def _generate_diff_for_change(change, commit_id):
    """Generates the diff for a single file change."""
    item = change.get('item', {})
    if item.get('gitObjectType') == 'tree':
        return ""

    change_type = change.get('changeType')
    file_path = item.get('path')
    
    original_content = ""
    modified_content = ""
    headers = _create_pat_auth_headers()

    if change_type == 'edit':
        modified_content = _get_item_content(file_path, commit_id)
        
        commit_details_url = f"{config.AZURE_DEVOPS_INSTANCE}/{config.AZURE_DEVOPS_COLLECTION}/{config.AZURE_DEVOPS_PROJECT}/_apis/git/repositories/{config.AZURE_DEVOPS_REPOSITORY_NAME}/commits/{commit_id}?api-version=6.0"
        commit_details_response = requests.get(commit_details_url, headers=headers)
        commit_details_response.raise_for_status()
        commit_details = commit_details_response.json()
        parent_commit_id = commit_details.get('parents', [None])[0]

        if parent_commit_id:
            original_content = _get_item_content(file_path, parent_commit_id)

    elif change_type == 'add':
        modified_content = _get_item_content(file_path, commit_id)

    elif change_type == 'delete':
        commit_details_url = f"{config.AZURE_DEVOPS_INSTANCE}/{config.AZURE_DEVOPS_COLLECTION}/{config.AZURE_DEVOPS_PROJECT}/_apis/git/repositories/{config.AZURE_DEVOPS_REPOSITORY_NAME}/commits/{commit_id}?api-version=6.0"
        commit_details_response = requests.get(commit_details_url, headers=headers)
        commit_details_response.raise_for_status()
        commit_details = commit_details_response.json()
        parent_commit_id = commit_details.get('parents', [None])[0]

        if parent_commit_id:
            original_content = _get_item_content(file_path, parent_commit_id)

    diff = difflib.unified_diff(
        original_content.splitlines(keepends=True),
        modified_content.splitlines(keepends=True),
        fromfile=f'a/{file_path}',
        tofile=f'b/{file_path}',
    )
    
    diff_text = "".join(diff)
    if diff_text:
        return f"--- Diff for {file_path} ---\n{diff_text}\n\n"
    return ""

def get_commit_changes(commit):
    """
    Fetches file changes, generates a diff, saves it and metadata to files, 
    and returns their paths.
    """
    commit_id = commit.get('commitId')
    commit_date = commit.get('author', {}).get('date')
    
    logging.info(f"Fetching changes for commit {commit_id}...")
    url = f"{config.AZURE_DEVOPS_INSTANCE}/{config.AZURE_DEVOPS_COLLECTION}/{config.AZURE_DEVOPS_PROJECT}/_apis/git/repositories/{config.AZURE_DEVOPS_REPOSITORY_NAME}/commits/{commit_id}/changes?api-version=6.0"
    headers = _create_pat_auth_headers()
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        changes = response.json().get('changes', [])
        
        all_diff_text = "".join([
            _generate_diff_for_change(change, commit_id)
            for change in changes
        ])

        if not all_diff_text:
            logging.warning(f"No textual changes found to generate a diff file for commit {commit_id}.")
            return None, None

        diff_dir = "diff_reports"
        os.makedirs(diff_dir, exist_ok=True)
        
        diff_filename = _create_valid_filename(commit_id, commit_date, "diff")
        meta_filename = _create_valid_filename(commit_id, commit_date, "json")
        diff_filepath = os.path.join(diff_dir, diff_filename)
        meta_filepath = os.path.join(diff_dir, meta_filename)
        
        with open(diff_filepath, "w", encoding="utf-8") as f:
            f.write(all_diff_text)
        logging.info(f"Diff for commit {commit_id} saved to {diff_filepath}.")
        
        import json
        metadata = {
            "commit_id": commit_id,
            "author": commit.get('author', {}).get('name', 'N/A'),
            "message": commit.get('comment', ''),
            "date": commit_date,
            "work_items": commit.get('workItemsDetails', [])
        }
        with open(meta_filepath, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=4)
        logging.info(f"Metadata for commit {commit_id} saved to {meta_filepath}.")

        return diff_filepath, meta_filepath

    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching changes for commit {commit_id}: {e}")
        return None, None

