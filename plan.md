# Plan de Auditoría y Consolidación de Diffs

Este plan describe la estrategia para llevar a cabo la auditoría técnica de los 39 commits del repositorio `cer-suite-cl-local-core-cloud` correspondientes a los últimos 30 días, y generar el reporte final en Word y Markdown.

## Fases del Plan

### Fase 1: Extracción y Organización
1. Ejecutar la extracción de los diffs del repositorio para el período especificado (completado).
2. Crear la estructura del directorio con formato dinámico `Documentacion/Informes/YYYY-MM-DD-AZURE_DEVOPS_REPOSITORY_NAME` (completado).

### Fase 2: Auditoría Técnica Manual
1. Leer los metadatos y diferencias de cada uno de los 39 commits.
2. Agrupar los commits por temas o autores.
3. Evaluar la calidad del código, coherencia, complejidad técnica real y riesgos de seguridad.
4. Redactar las fichas de auditoría individuales para cada grupo de cambios.

### Fase 3: Generación del Reporte Consolidado
1. Escribir el informe en formato Markdown (`Informe_Analisis_DIFFs_2026-07-03.md`).
2. Convertir el informe a formato Word (.docx) utilizando el motor `report_docx_generator.py` para aplicar estilos premium.
3. Archivar los diffs de soporte junto al reporte generado.
