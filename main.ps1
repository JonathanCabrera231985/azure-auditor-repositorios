# main.ps1

# Get the directory where the script is located
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Set the location to the script's directory
Set-Location -Path $scriptDir

# Check if a virtual environment exists
$venvPath = Join-Path -Path $scriptDir -ChildPath "venv"
if (-not (Test-Path -Path $venvPath)) {
    Write-Host "Python virtual environment not found. Please run 'python -m venv venv' to create it."
    exit 1
}

# Activate the virtual environment
. (Join-Path -Path $venvPath -ChildPath "Scripts\Activate.ps1")

# Install dependencies from requirements.txt
pip install -r requirements.txt

# Run the main Python script
python main.py @args

# Deactivate the virtual environment (optional)
# Deactivate-Venv
