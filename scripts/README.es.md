# Carpeta `scripts`

Esta carpeta contiene **scripts auxiliares** del monorepo: automatizaciones de desarrollo, utilidades de mantenimiento, tareas repetitivas (setup, lint, migraciones, generación de datos, etc.) y tooling interno.

- **Propósito principal**: agrupar herramientas de soporte que no pertenecen a una app/agente/pipeline específico, pero facilitan el trabajo del equipo.
- **Recomendación**: documenta cada script (qué hace, parámetros, requisitos, ejemplos de uso) y procura que sean reproducibles (y seguros) en distintos entornos.

## Exportación nocturna de telemetría

Ejecuta el worker independiente desde la raíz con `uv run python scripts/nightly_export.py`. Exporta a `data/raw/telemetry_YYYY-MM-DD.csv` los eventos del día UTC anterior solo si el archivo aún no existe y luego ejecuta el CLI existente (`python data/pipelines/pipeline.py`). El CSV es una copia de auditoría; el pipeline sigue leyendo telemetría desde Supabase.

Aplica `services/brasaland-api/migrations/005_create_job_runs.sql` antes de la primera ejecución. Proporciona `SUPABASE_URL` y `SUPABASE_SECRET_KEY` o `SUPABASE_SERVICE_ROLE_KEY` al proceso. Para pruebas, define `TARGET_DATE=YYYY-MM-DD`. No inicies este worker dentro de FastAPI.

El cron del host está programado a las 02:00 UTC todos los días. Prepara primero el `.venv` del proyecto; después revisa `scripts/nightly_export.crontab`, sustituye la ruta del repositorio e instálalo para el usuario de despliegue con `crontab scripts/nightly_export.crontab`. Entrega las credenciales de Supabase mediante el entorno protegido de cron. Este proceso separado evita incorporar el scheduler al ciclo de vida de la API.
