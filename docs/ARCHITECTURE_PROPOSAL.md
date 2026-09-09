# ARCHITECTURE PROPOSAL
**To:** Nicolás Park, CTO
**From:** Backend Engineering Team
**Date:** September 2026
**Subject:** Propuesta de Arquitectura Backend para la Plataforma Digital de Brasaland

---

## 1. Patrón Arquitectónico: Monolito Modular Orientado a Dominios (DDD)

Para construir la nueva API central de Brasaland, propongo adoptar una arquitectura de **Monolito Modular** inspirada en los principios de *Domain-Driven Design* (DDD). 

**Justificación para Brasaland:**
El stack tecnológico actual de la empresa es mínimo, basándose en hojas de cálculo, sistemas POS fragmentados y aplicaciones obsoletas. Aunque la complejidad de operar en dos países con dos monedas (COP y USD) podría sugerir una arquitectura de microservicios, el equipo de tecnología es pequeño. Implementar microservicios desde cero introduciría una sobrecarga operativa (DevOps, latencia de red, despliegues complejos) que ralentizaría la entrega de valor. 

Un monolito modular nos permite mantener la simplicidad de un único repositorio y un único despliegue, pero impone una separación estricta del código basada en los departamentos y áreas funcionales de la empresa (Operaciones, Compras, Marketing, RRHH). Si en el futuro el área de Operaciones requiere escalar independientemente de RRHH, la estructura modular permitirá extraer ese dominio a un microservicio con un esfuerzo mínimo.

## 2. Estructura de Carpetas y Módulos

El proyecto FastAPI se organizará aislando las responsabilidades transversales (configuración, bases de datos) de la lógica de negocio, la cual se dividirá en módulos que reflejan la estructura organizativa de Brasaland.

```text
/backend
├── /app
│   ├── /core                 # Configuraciones globales, seguridad, CORS, base de datos
│   ├── /modules              # Dominios de negocio (El núcleo del monolito modular)
│   │   ├── /operations       # Ventas, locales, inventario (Felipe Guerrero)
│   │   ├── /supply_chain     # Proveedores, órdenes de compra (Lucía Fernández)
│   │   ├── /marketing        # Fidelización, clientes, CRM (Camila Ospina)
│   │   ├── /hr               # Empleados, onboarding, turnos (Ashley Turner)
│   │   └── /training         # Recetas, estándares, manuales (Jake Morrison)
│   ├── /shared               # Utilidades compartidas (ej. conversores de COP/USD, timezones)
│   └── main.py               # Punto de entrada de FastAPI, registro de Routers
├── pyproject.toml            # Gestión de dependencias
└── .env.example              # Plantilla de variables de entorno
```

**Criterio de separación:**
Cada carpeta dentro de `/modules` actuará como un ecosistema independiente. Tendrá sus propios modelos de base de datos (`models.py`), esquemas de validación de Pydantic (`schemas.py`), lógica de negocio (`services.py`) y controladores (`routers.py`). Un módulo no debe acceder directamente a la base de datos de otro módulo; debe comunicarse a través de los servicios (interfaces) definidos por el módulo propietario.

## 3. Organización de Endpoints y Routers

Aprovechando la clase `APIRouter` de FastAPI, agruparemos las rutas lógicamente por dominio bajo un prefijo común, facilitando la lectura y el control de acceso (RBAC). 

*   **Rutas de Operaciones (`/api/v1/operations`):**
    *   `/locations`: Gestión de los 14 locales físicos.
    *   `/sales`: Registro y telemetría de ventas en tiempo real.
    *   `/inventory`: Stock de ingredientes y alertas automáticas.
*   **Rutas de Supply Chain (`/api/v1/supply-chain`):**
    *   `/suppliers`: Gestión de los ~20 proveedores actuales.
    *   `/purchase-orders`: Consolidación de compras en ambos mercados.
*   **Rutas de Marketing & Clientes (`/api/v1/marketing`):**
    *   `/customers`: Perfiles de clientes y CRM.
    *   `/loyalty`: Gestión del nuevo programa "Brasa Points" digital.
*   **Rutas de RRHH (`/api/v1/hr`):**
    *   `/employees`: Gestión de la plantilla de 115 personas.
    *   `/attendance`: Registro de ausencias y vacaciones.

En `main.py`, estos routers se importarán e incluirán en la aplicación principal (`app.include_router(...)`), manteniendo el archivo raíz limpio.

## 4. Estándares y Convenciones de FastAPI

La estructura propuesta maximiza las capacidades nativas de FastAPI:
*   **Inyección de Dependencias (Dependency Injection):** Se utilizará para proveer sesiones de base de datos y verificar la autenticación en cada endpoint. Esto elimina código duplicado y facilita el testing (mocking).
*   **Pydantic para validación:** Todo el intercambio de datos entre el frontend y el backend estará tipado y validado mediante modelos Pydantic, garantizando que (por ejemplo) una petición de inventario no falle por un tipo de dato incorrecto.
*   **Asincronía (Async/Await):** Dado que el sistema requiere telemetría en tiempo real de los locales físicos y conexiones a bases de datos relacionales, todas las operaciones de I/O utilizarán librerías asíncronas (como `asyncpg` o Motor) para evitar bloquear el *Event Loop* del servidor.

## 5. Separación Frontend / Backend

Dado que se construirán múltiples interfaces (dashboards ejecutivos, portal interno de RRHH, app de fidelización), el backend será estrictamente una API RESTful desacoplada.

*   **Estrategia de Repositorios:** Se utilizará un enfoque **Polyrepo** (un repositorio para el backend y repositorios separados para las aplicaciones frontend/móvil). Esto permite despliegues independientes y evita que el equipo de frontend rompa el pipeline del backend.
*   **Variables de Entorno y Configuración:** El frontend nunca contendrá credenciales. Se comunicará con el backend a través de URLs definidas por variables de entorno (`NEXT_PUBLIC_API_URL` o similar). El backend usará `pydantic-settings` para cargar y validar sus propios secretos (tokens, URIs de DB) de forma segura.
*   **CORS (Cross-Origin Resource Sharing):** Al estar en dominios diferentes (ej. `api.brasaland.com` y `admin.brasaland.com`), se configurará el middleware `CORSMiddleware` en FastAPI en el directorio `/core`. Se establecerá una lista blanca (allow-list) estricta de orígenes permitidos (los dominios oficiales de Brasaland) para evitar peticiones no autorizadas desde sitios de terceros.
*   **Autenticación:** Se utilizará JWT (JSON Web Tokens) transmitidos en las cabeceras HTTP (`Authorization: Bearer <token>`).

## 6. Riesgos y Puntos de Atención

Si el equipo no sigue estrictamente las convenciones de esta arquitectura, nos exponemos a fallos críticos en el negocio:

1.  **Acoplamiento Espagueti entre Módulos:** Si un desarrollador del equipo de RRHH consulta directamente las tablas de la base de datos de Operaciones (en lugar de llamar a `operations_service.get_sales()`), romperemos el encapsulamiento. Cuando Operaciones cambie su esquema de base de datos, el módulo de RRHH fallará en cascada, destruyendo el propósito del monolito modular.
2.  **Mala gestión de Timezones y Monedas:** Brasaland opera en Colombia (COP) y Florida (USD). Si no establecemos por convención que la base de datos guarde *siempre* las fechas en formato UTC y los importes financieros como enteros (centavos) con su respectiva moneda, los dashboards de la CEO Mariana Restrepo mostrarán sumas irreales o reportes desfasados por las diferencias horarias.
3.  **Cuellos de botella por operaciones síncronas:** La generación de reportes semanales en PDF automatizados o la ingesta de telemetría de 14 locales puede bloquear la API si se ejecuta sincrónicamente. Es imperativo que el equipo utilice herramientas como Celery o Background Tasks de FastAPI para delegar estas tareas pesadas fuera del flujo principal de petición-respuesta.