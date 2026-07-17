import argparse
import logging
import json
import os
import shutil
from datetime import datetime

from azure_devops import get_recent_commits, get_commit_changes
from llm_analyzer import analyze_commit, generate_consolidated_report
from report_generator import generate_report, save_report
from report_docx_generator import convert_markdown_to_docx
import config

def valid_date(s):
    """Helper function to validate date format for argparse."""
    try:
        return datetime.strptime(s, "%Y-%m-%d").isoformat()
    except ValueError:
        msg = f"Not a valid date: '{s}'. Expected format: YYYY-MM-DD."
        raise argparse.ArgumentTypeError(msg)

def generate_diffs(args):
    """Fetches commits and generates diff files with metadata."""
    logging.info("--- Running in 'Generate Diffs Only' mode ---")
    commits = get_recent_commits(start_date=args.start_date)

    if not commits:
        logging.warning("No commits found in the specified period.")
        return

    for commit in commits:
        if not commit:
            logging.warning("Skipping invalid commit object.")
            continue
        
        logging.info(f"\n--- Generating diff for Commit: {commit.get('commitId')[:8]} by {commit.get('author', {}).get('name', 'N/A')} ---")
        
        get_commit_changes(commit)
    logging.info("\n--- Diff generation complete. ---")

def _get_task_description_from_work_items(work_items):
    """Formats work item details into a string for the LLM prompt."""
    if not work_items:
        return "No associated work items found."
    
    descriptions = []
    for wi in work_items:
        fields = wi.get('fields', {})
        wi_id = wi.get('id', 'N/A')
        wi_title = fields.get('System.Title', 'No title')
        wi_type = fields.get('System.WorkItemType', 'Unknown type')
        descriptions.append(f"- Work Item {wi_id} ({wi_type}): {wi_title}")
    return "\n".join(descriptions)

def analyze_diffs():
    """Finds existing diff and metadata files and sends them for analysis."""
    import glob
    import os
    logging.info("--- Running in 'Analyze Only' mode ---")
    diff_dir = "diff_reports"
    diff_files = glob.glob(os.path.join(diff_dir, "*.diff"))

    if not diff_files:
        logging.warning("No .diff files found in the 'diff_reports' directory to analyze.")
        return

    analyses = []
    for diff_filepath in diff_files:
        meta_filepath = diff_filepath.replace(".diff", ".json")
        
        try:
            logging.info(f"\n--- Analyzing diff file: {os.path.basename(diff_filepath)} ---")
            
            try:
                with open(meta_filepath, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
                commit_id = metadata.get("commit_id", "N/A")
                author = metadata.get("author", "N/A")
                commit_message = metadata.get("message", "N/A")
                work_items = metadata.get("work_items", [])
            except FileNotFoundError:
                logging.error(f"Metadata file not found for {diff_filepath}. Skipping.")
                continue
            except json.JSONDecodeError:
                logging.error(f"Error decoding JSON from {meta_filepath}. Skipping.")
                continue

            with open(diff_filepath, "r", encoding="utf-8") as f:
                diff_content = f.read()

            if not diff_content:
                logging.warning(f"Diff file {diff_filepath} is empty. Skipping.")
                continue

            task_description = _get_task_description_from_work_items(work_items)

            analysis = analyze_commit(
                commit_message=commit_message,
                code_diff=diff_content,
                task_description=task_description
            )

            analyses.append({
                "commit_id": commit_id,
                "author": author,
                "comment": commit_message,
                "analysis": analysis,
                "diff_file": diff_filepath,
                "task_description": task_description
            })
            
            # Save analysis to JSON metadata file on disk
            try:
                metadata["analysis"] = analysis
                with open(meta_filepath, "w", encoding="utf-8") as f:
                    json.dump(metadata, f, indent=4)
            except Exception as e:
                logging.error(f"Error saving analysis to metadata JSON in analyze_diffs: {e}")
            
            logging.info(f"Result: {analysis}")

        except Exception as e:
            logging.error(f"An error occurred while processing {diff_filepath}: {e}")

    logging.info("\n--- Analysis complete ---")
    report = generate_report(analyses)
    save_report(report)

def full_process(args):
    """Runs the full process of fetching, diffing, and analyzing."""
    logging.info("--- Running full audit process ---")
    commits = get_recent_commits(start_date=args.start_date)

    if not commits:
        logging.warning("No commits found in the specified period to analyze.")
        
        # Generar un reporte indicando que no hay commits
        current_date_str = datetime.now().strftime("%Y-%m-%d")
        folder_name = f"{current_date_str}-{config.AZURE_DEVOPS_REPOSITORY_NAME}"
        informes_dir = os.path.join("Documentacion", "Informes", folder_name)
        os.makedirs(informes_dir, exist_ok=True)
        
        report = f"# Reporte de Auditoría de Commits\n\nNo se encontraron commits en el período especificado (últimos {config.DAYS_TO_EXTRACT} días) para el repositorio `{config.AZURE_DEVOPS_REPOSITORY_NAME}`.\n"
        
        md_filepath = os.path.join(informes_dir, f"Informe_Analisis_DIFFs_{current_date_str}.md")
        with open(md_filepath, "w", encoding="utf-8") as f:
            f.write(report)
            
        word_filepath = os.path.join(informes_dir, f"Informe_Analisis_DIFFs_{current_date_str}.docx")
        convert_markdown_to_docx(report, word_filepath)
        
        logging.info("Generated empty report due to no commits.")
        return

    analyses = []
    for commit in commits:
        if not commit:
            logging.warning("Skipping an invalid commit object.")
            continue

        commit_id = commit.get('commitId')
        author = commit.get('author', {}).get('name', 'N/A')
        comment = commit.get('comment', '')

        logging.info(f"\n--- Analyzing Commit: {commit_id[:8]} by {author} ---")
        logging.info(f"Message: {comment}")

        diff_file_path, _ = get_commit_changes(commit)

        if not diff_file_path:
            logging.warning(f"Skipping analysis for commit {commit_id[:8]} as no diff file was generated.")
            continue
            
        try:
            with open(diff_file_path, "r", encoding="utf-8") as f:
                diff_content = f.read()
        except FileNotFoundError:
            logging.error(f"Error: Diff file {diff_file_path} not found. Skipping analysis for commit {commit_id[:8]}.")
            continue

        task_description = _get_task_description_from_work_items(commit.get('workItemsDetails', []))

        analysis = analyze_commit(
            commit_message=comment,
            code_diff=diff_content,
            task_description=task_description
        )

        analyses.append({
            "commit_id": commit_id,
            "author": author,
            "comment": comment,
            "analysis": analysis,
            "diff_file": diff_file_path,
            "task_description": task_description
        })
        
        # Save analysis to JSON metadata file on disk
        meta_filepath = diff_file_path.replace(".diff", ".json")
        if os.path.exists(meta_filepath):
            try:
                with open(meta_filepath, "r", encoding="utf-8") as f:
                    meta_data = json.load(f)
                meta_data["analysis"] = analysis
                with open(meta_filepath, "w", encoding="utf-8") as f:
                    json.dump(meta_data, f, indent=4)
            except Exception as e:
                logging.error(f"Error saving analysis to metadata JSON: {e}")
        
        logging.info(f"Result: {analysis}")

    logging.info("\n--- Audit Complete ---")
    report = generate_report(analyses)
    save_report(report)



def main():
    """
    Main function to orchestrate the Azure DevOps commit audit.
    """
    parser = argparse.ArgumentParser(description="Audit Azure DevOps commits.")
    parser.add_argument(
        "--start-date",
        type=valid_date,
        help="The start date for fetching commits (format: YYYY-MM-DD). Defaults to the number of days set in DAYS_TO_EXTRACT env var if not provided."
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level (default: INFO)."
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--generate-diffs-only",
        action="store_true",
        help="Only fetch commits and generate diff files. Does not call the LLM."
    )
    mode_group.add_argument(
        "--analyze-only",
        action="store_true",
        help="Analyze existing diff files in 'diff_reports' directory. Does not fetch commits."
    )
    args = parser.parse_args()

    # --- Setup Logging ---
    log_level = getattr(logging, args.log_level.upper())
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("audit.log"),
            logging.StreamHandler()
        ]
    )
    # --- End Setup Logging ---
    
    if args.generate_diffs_only:
        generate_diffs(args)
        process_and_archive_reports()
    elif args.analyze_only:
        analyze_diffs()
        process_and_archive_reports()
    else:
        full_process(args)
        process_and_archive_reports()

def process_and_archive_reports():
    """
    Reads all generated .diff and .json files in diff_reports,
    generates a consolidated analysis using LLM,
    creates a Word report, and archives the files to a date folder in Informes.
    """
    import glob
    logging.info("--- Generating consolidated report and archiving diff files ---")
    
    diff_dir = "diff_reports"
    diff_files = glob.glob(os.path.join(diff_dir, "*.diff"))
    
    if not diff_files:
        logging.warning("No .diff files found in the 'diff_reports' directory to process.")
        return
        
    commits_data = []
    processed_files = []
    
    # Read each diff and metadata json file
    for diff_filepath in diff_files:
        meta_filepath = diff_filepath.replace(".diff", ".json")
        if not os.path.exists(meta_filepath):
            logging.warning(f"Metadata file not found for {diff_filepath}. Skipping.")
            continue
            
        try:
            with open(meta_filepath, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            with open(diff_filepath, "r", encoding="utf-8") as f:
                diff_content = f.read()
                
            commits_data.append({
                "commit_id": metadata.get("commit_id", "N/A"),
                "author": metadata.get("author", "N/A"),
                "date": metadata.get("date", "N/A"),
                "message": metadata.get("message", "N/A"),
                "work_items": metadata.get("work_items", []),
                "diff_content": diff_content,
                "analysis": metadata.get("analysis", "No se generó análisis individual.")
            })
            
            processed_files.append(diff_filepath)
            processed_files.append(meta_filepath)
            
        except Exception as e:
            logging.error(f"Error reading diff or metadata for {diff_filepath}: {e}")
            
    if not commits_data:
        logging.warning("No valid commit data collected for report.")
        return

    # Use branch/repository name
    branch_name = config.AZURE_DEVOPS_REPOSITORY_NAME
    prompt_template_path = os.path.join("Documentacion", "PromptGeneraAnalisisDIFF.md")
    
    # Generate report using LLM
    markdown_report = generate_consolidated_report(commits_data, prompt_template_path, branch_name)
    
    # Folder name: Documentacion/Informes/YYYY-MM-DD-repo_name
    current_date_str = datetime.now().strftime("%Y-%m-%d")
    folder_name = f"{current_date_str}-{config.AZURE_DEVOPS_REPOSITORY_NAME}"
    informes_dir = os.path.join("Documentacion", "Informes", folder_name)
    os.makedirs(informes_dir, exist_ok=True)
    
    word_filename = f"Informe_Analisis_DIFFs_{current_date_str}.docx"
    word_filepath = os.path.join(informes_dir, word_filename)
    
    # Convert markdown to docx and save
    logging.info(f"Converting report to Word document: {word_filepath}")
    convert_markdown_to_docx(markdown_report, word_filepath)
    
    # Save the markdown report next to it as well, for transparency
    md_filepath = os.path.join(informes_dir, f"Informe_Analisis_DIFFs_{current_date_str}.md")
    with open(md_filepath, "w", encoding="utf-8") as f:
        f.write(markdown_report)
    
    # Move all processed diff/json files to the reports folder
    logging.info(f"Moving {len(processed_files)} analyzed files to {informes_dir}...")
    for filepath in processed_files:
        filename = os.path.basename(filepath)
        dest_filepath = os.path.join(informes_dir, filename)
        
        # If destination file already exists, remove it
        if os.path.exists(dest_filepath):
            try:
                os.remove(dest_filepath)
            except Exception as e:
                logging.warning(f"Could not remove existing file in destination {dest_filepath}: {e}")
                
        try:
            shutil.move(filepath, dest_filepath)
        except Exception as e:
            logging.error(f"Error moving file {filepath} to {dest_filepath}: {e}")
            
    logging.info("--- Consolidated report generated and files archived successfully ---")

if __name__ == "__main__":
    main()
