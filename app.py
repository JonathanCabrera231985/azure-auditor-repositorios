# app.py

import os
import sys
import shutil
import logging
import threading
import time
from datetime import datetime, timedelta
from flask import Flask, jsonify, render_template, request
import dotenv

# Load environment variables
dotenv.load_dotenv()

import config
from main import full_process, process_and_archive_reports
from azure_devops import get_recent_commits
from report_docx_generator import convert_markdown_to_docx

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
    
    # Hide the API key partially for security
    raw_key = os.getenv("LLM_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
    masked_key = ""
    if raw_key:
        masked_key = "••••••••" + raw_key[-6:] if len(raw_key) > 6 else "••••••••"
        
    return jsonify({
        "collection": os.getenv("AZURE_DEVOPS_COLLECTION", ""),
        "project": os.getenv("AZURE_DEVOPS_PROJECT", ""),
        "repository": os.getenv("AZURE_DEVOPS_REPOSITORY_NAME", ""),
        "days": os.getenv("DAYS_TO_EXTRACT", "30"),
        "apiKey": masked_key,
        "hasKey": bool(raw_key)
    })

def run_simulated_audit(repository, project, collection, days):
    """Generates a complete mock/simulated audit report using real commits where possible."""
    logging.info("--- Iniciando Auditoría en MODO SIMULACIÓN (Local/Offline) ---")
    current_date_str = datetime.now().strftime("%Y-%m-%d")
    folder_name = f"{current_date_str}-{repository}"
    informes_dir = os.path.join("Documentacion", "Informes", folder_name)
    os.makedirs(informes_dir, exist_ok=True)
    
    # Try fetching real commits from Azure DevOps
    commits = []
    try:
        logging.info(f"Conectando a Azure DevOps para consultar commits reales...")
        commits = get_recent_commits(start_date=None)
    except Exception as e:
        logging.warning(f"No se pudieron consultar commits en DevOps ({e}). Usando commits de demostración.")
        
    if not commits:
        logging.info("Generando commits simulados de demostración...")
        commits = [
            {
                "commitId": "4a71361e04ad93385baacca4208f2b6d4dba3297",
                "author": {"name": "rmunoz", "date": datetime.now().isoformat()},
                "comment": "fix: optimizar desbordamiento de memoria al procesar XML de facturas",
                "workItemsDetails": [{"id": "4281", "fields": {"System.Title": "Heap Memory Overflow Facturas", "System.WorkItemType": "Bug"}}]
            },
            {
                "commitId": "8ee58434c98e6ba35cd4fa2b64000dc41c55cf44",
                "author": {"name": "rmunoz", "date": (datetime.now() - timedelta(days=1)).isoformat()},
                "comment": "feat: agregar soporte multi-base de datos SQL en ArtsEcDataSourceConfig",
                "workItemsDetails": [{"id": "4392", "fields": {"System.Title": "Conexiones multi-datasource SQL", "System.WorkItemType": "Feature"}}]
            }
        ]
    else:
        logging.info(f"Se encontraron {len(commits)} commits reales para el reporte simulado.")

    # Build consolidated report in Markdown
    markdown_report = f"La rama revisada fue: {repository}\n\n"
    markdown_report += "A continuación se presenta la evaluación técnica (SIMULADA LOCAL) de los archivos de diferencias (diffs).\n\n"
    
    table_rows = []
    
    for idx, commit in enumerate(commits, start=1):
        commit_id = commit.get("commitId", "N/A")
        author = commit.get("author", {}).get("name", "N/A")
        date_str = commit.get("author", {}).get("date", "")
        
        try:
            date_formatted = datetime.fromisoformat(date_str.replace("Z", "+00:00")).strftime("%d/%m/%Y")
        except Exception:
            date_formatted = "Reciente"
            
        comment = commit.get("comment", "")
        
        # Simple rule-based mock analysis based on commit message
        verdict = "Coherente / Funcional"
        complexity = "Media"
        if any(w in comment.lower() for w in ["fix", "corregir", "bug", "error"]):
            verdict = "Coherente / Funcional"
            complexity = "Baja"
        elif any(w in comment.lower() for w in ["feat", "agregar", "implementar", "add"]):
            verdict = "Coherente / Funcional"
            complexity = "Alta"
        elif any(w in comment.lower() for w in ["docs", "readme", "comentario", "comment"]):
            verdict = "Insignificante / Cosmético"
            complexity = "Nula"
            
        markdown_report += f"### {idx}. Auditoría de Cambios en Módulo (Commit {commit_id[:8]})\n\n"
        markdown_report += f"**Técnico Responsable:** {author}\n\n"
        markdown_report += f"**Fecha del Cambio:** {date_formatted}\n\n"
        markdown_report += "Archivos Analizados:\n"
        markdown_report += "- src/main/java/app/controller/MainController.java (Simulado)\n"
        markdown_report += "- src/main/resources/application.yml (Simulado)\n\n"
        markdown_report += "Evidencia Técnica:\n"
        markdown_report += f"- Simulación de auditoría para el cambio: \"{comment}\"\n"
        markdown_report += "- Lógica de negocio analizada de manera exitosa localmente (Modo Offline).\n\n"
        markdown_report += "Resultado del Modelo:\n"
        markdown_report += f"- Veredicto: {verdict} (Simulado)\n"
        markdown_report += f"- Complejidad Técnica Real: {complexity}\n"
        markdown_report += f"- Explicación al PM: Simulación de análisis local para el mensaje: \"{comment}\".\n"
        markdown_report += "- Alerta de Auditoría: Ninguna (Simulación)\n\n"
        markdown_report += "---\n\n"
        
        val_rating = "Medio" if complexity == "Media" else ("Alto" if complexity == "Alta" else "Bajo")
        table_rows.append(f"| {date_formatted} | {author} | Commit {commit_id[:8]} | {val_rating} | Aprobar (Simulación) |")

    # Add Executive Summary table
    markdown_report += "Resumen Ejecutivo para Toma de Decisiones\n\n"
    markdown_report += "Este cuadro resume la información para que usted y el PM aprueben las horas reportadas.\n\n"
    markdown_report += "| Fecha | Técnico | Archivo / Módulo | Evaluación de Valor | Acción Recomendada |\n"
    markdown_report += "| :--- | :--- | :--- | :--- | :--- |\n"
    markdown_report += "\n".join(table_rows) + "\n"
    
    # Save Markdown report
    md_filepath = os.path.join(informes_dir, f"Informe_Analisis_DIFFs_{current_date_str}.md")
    with open(md_filepath, "w", encoding="utf-8") as f:
        f.write(markdown_report)
    logging.info(f"Reporte Markdown simulado guardado en {md_filepath}")
        
    # Save Word report (.docx)
    word_filepath = os.path.join(informes_dir, f"Informe_Analisis_DIFFs_{current_date_str}.docx")
    logging.info(f"Generando documento Word simulado en {word_filepath}...")
    convert_markdown_to_docx(markdown_report, word_filepath)
    
    # Mock archive actions: clear the temp diff_reports folder
    diff_dir = "diff_reports"
    if os.path.exists(diff_dir):
        try:
            shutil.rmtree(diff_dir)
            os.makedirs(diff_dir, exist_ok=True)
        except Exception:
            pass
            
    logging.info("--- Auditoría en MODO SIMULACIÓN completada exitosamente ---")
    return markdown_report, folder_name, md_filepath

@app.route('/api/generate', methods=['POST'])
def generate_report():
    data = request.json or {}
    collection = data.get('collection')
    project = data.get('project')
    repository = data.get('repository')
    days = data.get('days', '30')
    provider = data.get('provider', 'gemini')
    api_key = data.get('apiKey', '').strip()
    model_name = data.get('model', 'gemini-1.5-flash')
    simulation_mode = data.get('simulationMode', False)
    
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

    # Handle simulation mode
    if simulation_mode:
        try:
            markdown_content, folder_name, md_filepath = run_simulated_audit(repository, project, collection, days_int)
            run_logs = memory_log_handler.get_and_clear()
            return jsonify({
                "status": "success",
                "markdown": markdown_content,
                "folder": folder_name,
                "filepath": md_filepath,
                "logs": run_logs,
                "simulated": True
            })
        except Exception as e:
            run_logs = memory_log_handler.get_and_clear()
            return jsonify({
                "status": "error",
                "message": f"Error en Modo Simulación: {str(e)}",
                "logs": run_logs
            }), 500

    # Overwrite LLM configuration in memory if user supplied a non-masked new key
    if api_key and not api_key.startswith("••••"):
        config.LLM_API_KEY = api_key
    
    # Overwrite LLM Provider and Model in memory
    config.LLM_PROVIDER = provider
    config.LLM_MODEL_NAME = model_name

    # Validate LLM Key only if using Gemini
    if provider == 'gemini' and not config.LLM_API_KEY:
        return jsonify({
            "status": "error",
            "message": "Se requiere una clave API de Gemini válida para continuar con este proveedor. Por favor ingrésela en el formulario o configúrela en el archivo .env.",
            "logs": ["ERROR: Falta Gemini API Key."]
        }), 400

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
        logging.info(f"Iniciando auditoría técnica real con Proveedor: '{provider.upper()}' y Modelo: '{model_name}'...")
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
                "logs": run_logs,
                "simulated": False
            })
        else:
            return jsonify({
                "status": "error", 
                "message": "El proceso finalizó pero no se pudo generar el archivo del reporte. Verifique los logs o que el token de DevOps y la clave API de Gemini sean correctos.",
                "logs": run_logs
            }), 500

    except Exception as e:
        run_logs = memory_log_handler.get_and_clear()
        return jsonify({
            "status": "error", 
            "message": f"Error de generación API de Gemini: {str(e)}",
            "logs": run_logs
        }), 500

@app.route('/api/exit', methods=['POST'])
def exit_app():
    def shutdown():
        time.sleep(0.5)
        os._exit(0)
    threading.Thread(target=shutdown).start()
    return jsonify({"status": "success", "message": "Servidor finalizado exitosamente."})

if __name__ == '__main__':
    print("\n" + "="*60)
    print("  Azure DevOps Auditor Web Server running at http://127.0.0.1:5000")
    print("="*60 + "\n")
    app.run(host='127.0.0.1', port=5000, debug=False)
