# Azure DevOps Commit Auditor

This script is a middleware tool that audits recent commits in an Azure DevOps Server repository. It uses a Large Language Model (LLM) to analyze whether the code changes in each commit align with the developer's commit message and the associated work item. It then generates a summary report for a Project Manager.

## How It Works

1.  **Extract**: Fetches all commits from the specified Azure DevOps repository within a given timeframe (defaulting to the last 24 hours).
2.  **Enrich**: For each commit, it fetches the details of any linked work items (e.g., User Stories, Bugs, Tasks) to understand the context of the change.
3.  **Process**: It retrieves the file changes for each commit and generates a textual diff.
4.  **Evaluate**: It sends the commit message, the associated work item description, and the code diff to an LLM (e.g., Gemini) with a specialized prompt, asking it to act as a senior software auditor.
5.  **Report**: It compiles the LLM's analyses into a single, easy-to-read Markdown report (`report.md`) that classifies each commit as "Substantial", "Moderate", or "Insignificant/Cosmetic".

## Prerequisites

*   Python 3.9+
*   Network access to your Azure DevOps Server instance.
*   An Azure DevOps Personal Access Token (PAT) with the following permissions:
    *   `Code (Read)`
    *   `Work Items (Read)`
*   An API key for a Gemini-compatible LLM.

## Setup

1.  **Clone the repository or download the files.**

2.  **Install the required Python packages:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure your environment variables:**
    -   Create a file named `.env` in the project root directory by copying the example file (`copy .env.example .env` or `cp .env.example .env`).
    -   Open the `.env` file and fill in the values for your environment:
        -   `AZURE_DEVOPS_INSTANCE`: The URL of your Azure DevOps organization (e.g., `https://dev.azure.com/your-org`).
        -   `AZURE_DEVOPS_COLLECTION`: Your project collection. For Azure DevOps Services, this is typically the same as your organization name.
        -   `AZURE_DEVOPS_PROJECT`: The name of your project.
        -   `AZURE_DEVOPS_REPOSITORY_NAME`: The name of the repository you want to audit.
        -   `AZURE_DEVOPS_PAT`: Your Personal Access Token.
        -   `LLM_API_KEY`: Your API key for the language model.

## Usage

Run the main script from the project's root directory with optional flags.

### Full Process (Default)

This runs the end-to-end process: fetching commits, generating diffs, and analyzing them.

```bash
python main.py
```

### Command-Line Arguments

*   `--start-date YYYY-MM-DD`: Specify a start date for fetching commits. If omitted, it defaults to the last 24 hours.
    ```bash
    python main.py --start-date 2023-10-25
    ```
*   `--log-level [DEBUG|INFO|WARNING|ERROR|CRITICAL]`: Set the logging verbosity. Defaults to `INFO`.
    ```bash
    python main.py --log-level DEBUG
    ```

### Execution Modes

You can run specific parts of the process using the following flags:

*   `--generate-diffs-only`: Fetches commits from Azure DevOps and saves the diffs and their metadata (commit message, author, work items) to the `diff_reports/` directory. This mode does not call the LLM and is useful for pre-fetching data.

    ```bash
    python main.py --generate-diffs-only
    ```

*   `--analyze-only`: Analyzes the pre-generated diff and metadata files from the `diff_reports/` directory. This mode does not connect to Azure DevOps. It is useful for re-running the analysis with a different model or prompt without re-fetching the data.

    ```bash
    python main.py --analyze-only
    ```

## Output

*   **`report.md`**: A Markdown file containing the full audit summary.
*   **`audit.log`**: A log file containing detailed information about the script's execution. This file is ignored by git.
*   **`diff_reports/`**: A directory containing the generated diff and metadata files. This directory is also ignored by git.
