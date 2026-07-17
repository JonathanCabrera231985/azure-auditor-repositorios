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

import json
import config
from main import generate_diffs, analyze_diffs, process_and_archive_reports
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

def write_mock_diffs(repository):
    diff_dir = "diff_reports"
    os.makedirs(diff_dir, exist_ok=True)
    
    # Mock 1
    meta1 = {
        "commit_id": "4a71361e04ad93385baacca4208f2b6d4dba3297",
        "author": "rmunoz",
        "date": datetime.now().isoformat(),
        "message": "fix: optimizar desbordamiento de memoria al procesar XML de facturas",
        "work_items": [{"id": "4281", "fields": {"System.Title": "Heap Memory Overflow Facturas", "System.WorkItemType": "Bug"}}]
    }
    diff1 = "--- src/main/java/app/controller/MainController.java\n+++ src/main/java/app/controller/MainController.java\n@@ -10,4 +10,4 @@\n-public void processInvoice() {\n+public void processInvoiceStreaming() {\n"
    
    with open(os.path.join(diff_dir, "mock_1.json"), "w", encoding="utf-8") as f:
        json.dump(meta1, f, indent=4)
    with open(os.path.join(diff_dir, "mock_1.diff"), "w", encoding="utf-8") as f:
        f.write(diff1)
        
    # Mock 2
    meta2 = {
        "commit_id": "8ee58434c98e6ba35cd4fa2b64000dc41c55cf44",
        "author": "rmunoz",
        "date": (datetime.now() - timedelta(days=1)).isoformat(),
        "message": "feat: agregar soporte multi-base de datos SQL en ArtsEcDataSourceConfig",
        "work_items": [{"id": "4392", "fields": {"System.Title": "Conexiones multi-datasource SQL", "System.WorkItemType": "Feature"}}]
    }
    diff2 = "--- src/main/resources/application.yml\n+++ src/main/resources/application.yml\n@@ -5,2 +5,5 @@\n+  datasource:\n+    secondary:\n+      url: jdbc:sqlserver://localhost\n"
    
    with open(os.path.join(diff_dir, "mock_2.json"), "w", encoding="utf-8") as f:
        json.dump(meta2, f, indent=4)
    with open(os.path.join(diff_dir, "mock_2.diff"), "w", encoding="utf-8") as f:
        f.write(diff2)

def run_simulated_audit_on_extracted_diffs(repository):
    logging.info("--- Iniciando Auditoría en MODO SIMULACIÓN (Local/Offline) ---")
    current_date_str = datetime.now().strftime("%Y-%m-%d")
    folder_name = f"{current_date_str}-{repository}"
    informes_dir = os.path.join("Documentacion", "Informes", folder_name)
    os.makedirs(informes_dir, exist_ok=True)
    
    import glob
    diff_files = glob.glob(os.path.join("diff_reports", "*.diff"))
    
    if not diff_files:
        logging.warning("No .diff files found to process in simulation.")
        return "No commits found to audit.", folder_name, ""
        
    commits_data = []
    processed_files = []
    
    for diff_filepath in diff_files:
        meta_filepath = diff_filepath.replace(".diff", ".json")
        if not os.path.exists(meta_filepath):
            continue
        try:
            with open(meta_filepath, "r", encoding="utf-8") as f:
                meta = json.load(f)
            processed_files.append(diff_filepath)
            processed_files.append(meta_filepath)
            
            comment = meta.get("message", "")
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
                
            analysis = f"{verdict}: Análisis local simulado para '{comment}'."
            meta["analysis"] = analysis
            
            commits_data.append({
                "commit_id": meta.get("commit_id", "N/A"),
                "author": meta.get("author", "N/A"),
                "date": meta.get("date", "N/A"),
                "message": comment,
                "work_items": meta.get("work_items", []),
                "analysis": analysis
            })
        except Exception as e:
            logging.error(f"Error reading file in simulation: {e}")
            
    markdown_report = f"La rama revisada fue: {repository}\n\n"
    markdown_report += "A continuación se presenta la evaluación técnica (SIMULADA LOCAL) de los archivos de diferencias (diffs).\n\n"
    
    table_rows = []
    for idx, item in enumerate(commits_data, start=1):
        commit_id = item.get("commit_id", "N/A")
        author = item.get("author", "N/A")
        date_str = item.get("date", "")
        comment = item.get("message", "")
        analysis_text = item.get("analysis", "")
        
        complexity = "Media"
        if "Baja" in analysis_text: complexity = "Baja"
        elif "Alta" in analysis_text: complexity = "Alta"
        elif "Nula" in analysis_text: complexity = "Nula"
        
        try:
            date_formatted = datetime.fromisoformat(date_str.replace("Z", "+00:00")).strftime("%d/%m/%Y")
        except Exception:
            date_formatted = "Reciente"
            
        markdown_report += f"### {idx}. Auditoría de Cambios en Módulo (Commit {commit_id[:8]})\n\n"
        markdown_report += f"**Técnico Responsable:** {author}\n\n"
        markdown_report += f"**Fecha del Cambio:** {date_formatted}\n\n"
        markdown_report += "Archivos Analizados:\n"
        markdown_report += "- src/main/java/app/controller/MainController.java (Simulado)\n\n"
        markdown_report += "Evidencia Técnica:\n"
        markdown_report += f"- Simulación de auditoría para el cambio: \"{comment}\"\n"
        markdown_report += "- Lógica de negocio analizada de manera exitosa localmente (Modo Offline).\n\n"
        markdown_report += "Resultado del Modelo:\n"
        markdown_report += f"- Veredicto: Coherente / Funcional (Simulado)\n"
        markdown_report += f"- Complejidad Técnica Real: {complexity}\n"
        markdown_report += f"- Explicación al PM: Simulación de auditoría local para el mensaje: \"{comment}\".\n"
        markdown_report += "- Alerta de Auditoría: Ninguna (Simulación)\n\n"
        markdown_report += "---\n\n"
        
        val_rating = "Medio" if complexity == "Media" else ("Alto" if complexity == "Alta" else "Bajo")
        table_rows.append(f"| {date_formatted} | {author} | Commit {commit_id[:8]} | {val_rating} | Aprobar (Simulación) |")

    markdown_report += "Resumen Ejecutivo para Toma de Decisiones\n\n"
    markdown_report += "Este cuadro resume la información para que usted y el PM aprueben las horas reportadas.\n\n"
    markdown_report += "| Fecha | Técnico | Archivo / Módulo | Evaluación de Valor | Acción Recomendada |\n"
    markdown_report += "| :--- | :--- | :--- | :--- | :--- |\n"
    markdown_report += "\n".join(table_rows) + "\n"
    
    md_filepath = os.path.join(informes_dir, f"Informe_Analisis_DIFFs_{current_date_str}.md")
    with open(md_filepath, "w", encoding="utf-8") as f:
        f.write(markdown_report)
        
    word_filepath = os.path.join(informes_dir, f"Informe_Analisis_DIFFs_{current_date_str}.docx")
    convert_markdown_to_docx(markdown_report, word_filepath)
    
    for filepath in processed_files:
        filename = os.path.basename(filepath)
        dest_filepath = os.path.join(informes_dir, filename)
        if os.path.exists(dest_filepath):
            try:
                os.remove(dest_filepath)
            except Exception:
                pass
        try:
            shutil.move(filepath, dest_filepath)
        except Exception:
            pass
            
    logging.info("--- Auditoría en MODO SIMULACIÓN completada exitosamente ---")
    return markdown_report, folder_name, md_filepath

@app.route('/api/check_diffs', methods=['GET'])
def check_diffs():
    diff_dir = "diff_reports"
    count = 0
    has_diffs = False
    if os.path.exists(diff_dir):
        import glob
        diff_files = glob.glob(os.path.join(diff_dir, "*.diff"))
        count = len(diff_files)
        has_diffs = count > 0
    return jsonify({
        "hasDiffs": has_diffs,
        "count": count
    })

@app.route('/api/extract', methods=['POST'])
def extract_diffs():
    data = request.json or {}
    collection = data.get('collection')
    project = data.get('project')
    repository = data.get('repository')
    days = data.get('days', '30')
    simulation_mode = data.get('simulationMode', False)
    
    if not all([collection, project, repository]):
        return jsonify({"status": "error", "message": "Todos los campos de DevOps son requeridos."}), 400
        
    try:
        days_int = int(days)
    except ValueError:
        return jsonify({"status": "error", "message": "El número de días debe ser un número entero válido."}), 400

    # Override configuration in memory
    config.AZURE_DEVOPS_COLLECTION = collection
    config.AZURE_DEVOPS_PROJECT = project
    config.AZURE_DEVOPS_REPOSITORY_NAME = repository
    config.DAYS_TO_EXTRACT = days_int

    # Clear logs and prepare folder
    memory_log_handler.get_and_clear()
    
    diff_dir = "diff_reports"
    if os.path.exists(diff_dir):
        try:
            shutil.rmtree(diff_dir)
        except Exception as e:
            logging.warning(f"Could not clean diff_reports: {e}")
    os.makedirs(diff_dir, exist_ok=True)

    if simulation_mode:
        try:
            logging.info("Generando archivos diff de simulación (Modo Offline)...")
            write_mock_diffs(repository)
            run_logs = memory_log_handler.get_and_clear()
            return jsonify({
                "status": "success",
                "count": 2,
                "logs": run_logs
            })
        except Exception as e:
            run_logs = memory_log_handler.get_and_clear()
            return jsonify({
                "status": "error",
                "message": f"Error al generar diffs simulados: {str(e)}",
                "logs": run_logs
            }), 500

    class AuditArgs:
        def __init__(self, days_val):
            self.start_date = None
            self.generate_diffs_only = True
            self.analyze_only = False
            self.log_level = "INFO"

    try:
        logging.info(f"Iniciando extracción de Diffs para {repository} ({days_int} días)...")
        args = AuditArgs(days_int)
        
        generate_diffs(args)
        
        import glob
        count = len(glob.glob(os.path.join(diff_dir, "*.diff")))
        
        run_logs = memory_log_handler.get_and_clear()
        return jsonify({
            "status": "success",
            "count": count,
            "logs": run_logs
        })
    except Exception as e:
        run_logs = memory_log_handler.get_and_clear()
        return jsonify({
            "status": "error",
            "message": f"Error al extraer diffs: {str(e)}",
            "logs": run_logs
        }), 500

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
        return jsonify({"status": "error", "message": "Todos los campos de DevOps son requeridos."}), 400
        
    try:
        days_int = int(days)
    except ValueError:
        return jsonify({"status": "error", "message": "El número de días debe ser un número entero válido."}), 400

    # Override configuration
    config.AZURE_DEVOPS_COLLECTION = collection
    config.AZURE_DEVOPS_PROJECT = project
    config.AZURE_DEVOPS_REPOSITORY_NAME = repository
    config.DAYS_TO_EXTRACT = days_int

    # Clear logs
    memory_log_handler.get_and_clear()

    # Handle simulation mode
    if simulation_mode:
        try:
            markdown_content, folder_name, md_filepath = run_simulated_audit_on_extracted_diffs(repository)
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
                "message": f"Error en Simulación de Reporte: {str(e)}",
                "logs": run_logs
            }), 500

    # Overwrite LLM configuration in memory if user supplied a non-masked new key
    if api_key and not api_key.startswith("••••"):
        config.LLM_API_KEY = api_key
    
    config.LLM_PROVIDER = provider
    config.LLM_MODEL_NAME = model_name

    # Validate LLM Key only if using Gemini
    if provider == 'gemini' and not config.LLM_API_KEY:
        return jsonify({
            "status": "error",
            "message": "Se requiere una clave API de Gemini válida para continuar con este proveedor. Por favor ingrésela en el formulario o configúrela en el archivo .env.",
            "logs": ["ERROR: Falta Gemini API Key."]
        }), 400

    class AuditArgs:
        def __init__(self, days_val):
            self.start_date = None
            self.generate_diffs_only = False
            self.analyze_only = True
            self.log_level = "INFO"

    try:
        logging.info(f"Iniciando análisis y generación de reporte consolidado con Proveedor: '{provider.upper()}' y Modelo: '{model_name}'...")
        
        # Verify if there are any diff files to analyze
        import glob
        diff_dir = "diff_reports"
        diff_files = glob.glob(os.path.join(diff_dir, "*.diff"))
        if not diff_files:
            return jsonify({
                "status": "error",
                "message": "No se encontraron archivos .diff en la carpeta temporal para analizar. Asegúrese de hacer clic primero en 'Extraer Diffs'.",
                "logs": ["ERROR: No hay archivos diff disponibles."]
            }), 400

        # Execute only analysis and archiving
        analyze_diffs()
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
                "message": "El proceso finalizó pero no se pudo generar el archivo del reporte consolidado.",
                "logs": run_logs
            }), 500

    except Exception as e:
        run_logs = memory_log_handler.get_and_clear()
        return jsonify({
            "status": "error", 
            "message": f"Error de análisis/generación: {str(e)}",
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
