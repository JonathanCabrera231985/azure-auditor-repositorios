# llm_analyzer.py

import os
import google.generativeai as genai
import logging
import config

def analyze_commit(commit_message, code_diff, task_description=""):
    """
    Analyzes the significance of a code commit using the Gemini API.
    """
    if not code_diff:
        logging.warning("Skipping analysis because code diff is empty.")
        return "Analysis skipped: No code changes provided."

    logging.info("Sending data to Gemini for analysis...")
    
    try:
        genai.configure(api_key=config.LLM_API_KEY)
        
        # The prompt is a combination of the previous system and user prompts,
        # formatted for a direct text-generation model like Gemini.
        prompt = f"""
        You are a Senior Software Auditor and an expert in estimating software development effort. Your task is to analyze a developer's commit and determine if the work done is substantial and aligns with their stated claim.

        Analyze the following software commit.

        **Developer's Claim:**
        - Commit Message: "{commit_message}"
        - Associated Task Description: "{task_description if task_description else 'Not provided.'}"

        **Evidence (Code Changes):**
        ```diff
        {code_diff}
        ```

        **Your Task:**
        1.  Assess if the code changes reflect the developer's claim.
        2.  Determine the significance of the work. Ignore purely cosmetic changes like whitespace, formatting, or adding comments unless they are exceptionally substantive.
        3.  Provide a concise, one-line summary for a non-technical Project Manager.

        **Output Format:**
        Start your response with one of three classifications, followed by a brief justification.
        - **Substantial:** (Use for significant new features, complex bug fixes, or major refactoring.)
        - **Moderate:** (Use for minor features, simple bug fixes, or meaningful improvements.)
        - **Insignificant/Cosmetic:** (Use for formatting, comments, documentation, or trivial changes that don't affect functionality.)

        Example: "Substantial: The developer implemented the entire user authentication flow as described."
        Example: "Insignificant/Cosmetic: The changes only involve re-indenting code and adding comments."
        """

        model = genai.GenerativeModel('models/gemini-3-pro-preview')
        response = model.generate_content(prompt)
        
        analysis = response.text.strip()
        logging.info("LLM analysis received.")
        return analysis

    except Exception as e:
        logging.error(f"An error occurred during Gemini analysis: {e}")
        return "Could not get analysis due to an error."


def generate_consolidated_report(commits_data, prompt_template_path, branch_name="Main"):
    """
    Calls the Gemini LLM with the consolidated system prompt and all diffs + metadata,
    and returns the generated report in markdown.
    Checks first if a manual template file exists at Documentacion/Informe_Analisis_DIFFs_Template.md.
    """
    manual_template = os.path.join("Documentacion", "Informe_Analisis_DIFFs_Template.md")
    if os.path.exists(manual_template):
        logging.info(f"Loading manual analysis template from {manual_template}...")
        try:
            with open(manual_template, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logging.error(f"Error reading manual template: {e}")

    if not commits_data:
        logging.warning("No commit data provided for consolidated report.")
        return "No commits found to audit."

    try:
        # Load prompt template
        with open(prompt_template_path, "r", encoding="utf-8") as f:
            prompt_template = f.read()

        # Format input data representing all commits and their diffs
        input_data_parts = []
        for index, commit in enumerate(commits_data, start=1):
            commit_id = commit.get("commit_id", "N/A")
            author = commit.get("author", "N/A")
            date = commit.get("date", "N/A")
            message = commit.get("message", "N/A")
            
            # Format work items details
            work_items = commit.get("work_items", [])
            work_items_str_list = []
            if work_items:
                for wi in work_items:
                    fields = wi.get('fields', {})
                    wi_id = wi.get('id', 'N/A')
                    wi_title = fields.get('System.Title', 'No title')
                    wi_type = fields.get('System.WorkItemType', 'Unknown type')
                    work_items_str_list.append(f"- Work Item {wi_id} ({wi_type}): {wi_title}")
                work_items_str = "\n".join(work_items_str_list)
            else:
                work_items_str = "No associated work items."
                
            diff_content = commit.get("diff_content", "No changes / empty diff.")

            part = f"""--- COMMIT {index} ---
Commit ID: {commit_id}
Técnico Responsable: {author}
Fecha del Cambio: {date}
Commit Message: {message}
Associated Work Items:
{work_items_str}

Diff changes:
```diff
{diff_content}
```
"""
            input_data_parts.append(part)

        all_commits_input = "\n\n".join(input_data_parts)
        
        # Replace template placeholders
        prompt = prompt_template.replace("{nombre_rama_detectado_en_input}", branch_name)
        
        # Append the input data to the prompt
        full_prompt = f"""{prompt}

# INPUT DATA TO ANALYZE

Repository/Branch: {branch_name}

{all_commits_input}
"""

        logging.info("Sending consolidated diff data to Gemini for analysis...")
        genai.configure(api_key=config.LLM_API_KEY)
        
        model = genai.GenerativeModel('models/gemini-3-pro-preview')
        response = model.generate_content(full_prompt)
        
        analysis = response.text.strip()
        logging.info("Consolidated LLM analysis received.")
        return analysis

    except Exception as e:
        logging.error(f"An error occurred during consolidated Gemini analysis: {e}")
        return f"Could not generate consolidated analysis due to an error: {e}"

