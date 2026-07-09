# report_generator.py
import logging
from datetime import datetime

def generate_report(analyses):
    """
    Generates a markdown report from the commit analyses.
    """
    logging.info("Generating report...")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    report = f"# Azure DevOps Commit Audit Report\n\n"
    report += f"**Report Generated:** {now}\n\n"
    report += "---\n\n"

    if not analyses:
        report += "No recent commits were found or analyzed.\n"
        return report

    # Group analyses by their classification
    grouped_analyses = {
        "Substantial": [],
        "Moderate": [],
        "Insignificant/Cosmetic": [],
        "Other": []
    }

    for analysis_item in analyses:
        analysis_text = analysis_item['analysis']
        if analysis_text.startswith("Substantial"):
            grouped_analyses["Substantial"].append(analysis_item)
        elif analysis_text.startswith("Moderate"):
            grouped_analyses["Moderate"].append(analysis_item)
        elif analysis_text.startswith("Insignificant/Cosmetic"):
            grouped_analyses["Insignificant/Cosmetic"].append(analysis_item)
        else:
            grouped_analyses["Other"].append(analysis_item)

    # Build report sections
    for category, items in grouped_analyses.items():
        if items:
            report += f"## {category} Commits\n\n"
            for item in items:
                report += f"**Commit:** `{item['commit_id'][:12]}` by **{item['author']}**\n"
                report += f"**Message:** {item['comment']}\n"
                
                # Add associated task description if it exists
                task_desc = item.get('task_description')
                if task_desc and task_desc != "No associated work items found.":
                    report += f"**Associated Task(s):**\n{task_desc}\n"

                report += f"**Audit Finding:** {item['analysis']}\n"
                if item.get('diff_file'):
                    report += f"**Diff File:** `{item['diff_file']}`\n"
                report += "---\n"
            report += "\n"
            
    logging.info("Report generation complete.")
    return report

def save_report(report_content, filename="report.md"):
    """
    Saves the report content to a file.
    """
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(report_content)
        logging.info(f"Report successfully saved to {filename}")
    except IOError as e:
        logging.error(f"Error saving report to file: {e}")

