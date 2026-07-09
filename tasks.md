# Checklist de Tareas – Auditoría DevOps

- [x] Agregar parámetro `DAYS_TO_EXTRACT` en el archivo `.env`.
- [x] Desarrollar el generador de Word `report_docx_generator.py` para conversión de Markdown a `.docx`.
- [x] Modificar la orquestación en `main.py` para automatizar el guardado y movimiento a carpetas fechadas.
- [x] Configurar la nomenclatura dinámica de la carpeta de destino (`YYYY-MM-DD-AZURE_DEVOPS_REPOSITORY_NAME`).
- [/] Leer y realizar la auditoría técnica de los 39 commits extraídos del repositorio.
- [ ] Redactar el reporte consolidado `Informe_Analisis_DIFFs_2026-07-03.md` en base al prompt de auditoría.
- [ ] Ejecutar el conversor para generar el documento de Word final `Informe_Analisis_DIFFs_2026-07-03.docx`.
- [ ] Archivar los 78 archivos (.diff y .json) en la carpeta destino correspondiente.
