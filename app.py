# app.py

import os
import sys
import shutil
import logging
import threading
import time
from datetime import datetime
from flask import Flask, jsonify, render_template, request
import dotenv

# Load environment variables
dotenv.load_dotenv()

import config
from main import full_process, process_and_archive_reports

app = Flask(__name__)

# Setup custom logging handler to capture auditor logs
class MemoryLogHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.logs = []

    def emit(self, record):
        log_entry = self.format(record)
        self.logs.append(log_entry)

    def get_and_clear(self):
        temp = list(self.logs)
        self.logs.clear()
        return temp

memory_log_handler = MemoryLogHandler()
memory_log_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logging.getLogger().addHandler(memory_log_handler)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/config', methods=['GET'])
def get_config():
    # Load fresh config from .env files or fallback
    dotenv.load_dotenv(override=True)
    return jsonify({
        "collection": os.getenv("AZURE_DEVOPS_COLLECTION", ""),
        "project": os.getenv("AZURE_DEVOPS_PROJECT", ""),
        "repository": os.getenv("AZURE_DEVOPS_REPOSITORY_NAME", ""),
        "days": os.getenv("DAYS_TO_EXTRACT", "30")
    })

@app.route('/api/generate', methods=['POST'])
def generate_report():
    data = request.json or {}
    collection = data.get('collection')
    project = data.get('project')
    repository = data.get('repository')
    days = data.get('days', '30')
    
    if not all([collection, project, repository]):
        return jsonify({"status": "error", "message": "Todos los campos de DevOps (Colección, Proyecto, Repositorio) son requeridos."}), 400
        
    try:
        days_int = int(days)
    except ValueError:
        return jsonify({"status": "error", "message": "El número de días debe ser un número entero válido."}), 400

    # Override configuration in-memory for the current run
    config.AZURE_DEVOPS_COLLECTION = collection
    config.AZURE_DEVOPS_PROJECT = project
    config.AZURE_DEVOPS_REPOSITORY_NAME = repository
    config.DAYS_TO_EXTRACT = days_int

    # Clear logs before starting
    memory_log_handler.get_and_clear()

    # Clear diff_reports directory
    diff_dir = "diff_reports"
    if os.path.exists(diff_dir):
        try:
            shutil.rmtree(diff_dir)
        except Exception as e:
            logging.warning(f"Could not clean diff_reports: {e}")
    os.makedirs(diff_dir, exist_ok=True)

    class AuditArgs:
        def __init__(self, days_val):
            self.start_date = None
            self.generate_diffs_only = False
            self.analyze_only = False
            self.log_level = "INFO"

    try:
        logging.info(f"Iniciando auditoría técnica para Repositorio: '{repository}' en el Proyecto: '{project}'...")
        args = AuditArgs(days_int)
        
        # Execute audit processes
        full_process(args)
        process_and_archive_reports()

        # Locate the generated report
        current_date_str = datetime.now().strftime("%Y-%m-%d")
        folder_name = f"{current_date_str}-{repository}"
        informes_dir = os.path.join("Documentacion", "Informes", folder_name)
        md_filepath = os.path.join(informes_dir, f"Informe_Analisis_DIFFs_{current_date_str}.md")

        run_logs = memory_log_handler.get_and_clear()

        if os.path.exists(md_filepath):
            with open(md_filepath, "r", encoding="utf-8") as f:
                markdown_content = f.read()
            return jsonify({
                "status": "success",
                "markdown": markdown_content,
                "folder": folder_name,
                "filepath": md_filepath,
                "logs": run_logs
            })
        else:
            return jsonify({
                "status": "error", 
                "message": "El proceso finalizó pero no se pudo generar el archivo del reporte. Verifique que existan commits en el período especificado o que el PAT sea correcto.",
                "logs": run_logs
            }), 500

    except Exception as e:
        run_logs = memory_log_handler.get_and_clear()
        return jsonify({
            "status": "error", 
            "message": f"Error interno durante la generación: {str(e)}",
            "logs": run_logs
        }), 500

@app.route('/api/exit', methods=['POST'])
def exit_app():
    def shutdown():
        time.sleep(0.5)
        # Force terminate
        os._exit(0)
    threading.Thread(target=shutdown).start()
    return jsonify({"status": "success", "message": "Servidor finalizado exitosamente."})

if __name__ == '__main__':
    # Running locally
    print("\n" + "="*60)
    print("  Azure DevOps Auditor Web Server running at http://127.0.0.1:5000")
    print("="*60 + "\n")
    app.run(host='127.0.0.1', port=5000, debug=False)
