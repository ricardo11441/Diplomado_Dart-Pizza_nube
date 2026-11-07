# Dart Pizza AI — versión ejecutable local

Aplicación web funcional de gestión para una pizzería. Esta entrega convierte la estructura incompleta recibida en un MVP ejecutable con **FastAPI + SQLite + interfaz web responsive**. Se conserva el objetivo funcional del documento de requisitos; para facilitar la primera ejecución local, esta versión usa SQLite en lugar de exigir Oracle/PostgreSQL y no requiere Node.js.

## Incluye

- Inicio de sesión y registro de clientes; contraseñas con PBKDF2-HMAC-SHA256 y tokens firmados con expiración.
- Roles `admin`, `empleado` y `cliente`; autorización aplicada en los endpoints.
- Catálogo y gestión básica de productos (crear/editar como administrador).
- Carrito en la sesión del navegador y creación de pedidos con precio/stock validados en el backend.
- Consulta de pedidos y cambio de estado para administrador/empleado.
- Inventario de ingredientes con movimientos de entrada, salida y ajuste; alertas por mínimos.
- Dashboard, ventas acumuladas, ticket promedio, pendientes y productos más vendidos.
- Recomendaciones determinísticas y asistente analítico que consulta la base local.
- Usuarios y registro de auditoría.
- Datos de demostración claramente identificados por las cuentas `@dartpizza.local`.

## Requisitos

- Windows 10/11, macOS o Linux.
- Python 3.10 o superior.
- Conexión a internet solo para instalar dependencias la primera vez (y cargar la fuente tipográfica remota; la app funciona sin ella).

**No necesitas instalar Node.js, PostgreSQL, Oracle ni Ollama para esta versión local.**

## Ejecución rápida en Windows

1. Descomprime `DartPizzaAI.zip` en una carpeta, por ejemplo `C:\DartPizzaAI`.
2. Instala Python desde https://www.python.org/downloads/ y marca **Add Python to PATH**.
3. Haz doble clic en `INICIAR_DART_PIZZA.bat`.
4. Espera a que se instalen las dependencias y se inicie el servidor.
5. Abre http://127.0.0.1:8000 en Chrome, Edge o Firefox.
6. Para detenerlo, vuelve a la ventana negra y pulsa `Ctrl + C`.

La primera ejecución crea `data/dartpizza.db` automáticamente y carga los datos demo. No borres ese archivo si deseas conservar los datos que registres.

### Ejecución manual (Windows PowerShell)

```powershell
cd DartPizzaAI
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Ejecución manual (macOS / Linux)

```bash
cd DartPizzaAI
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

## Cuentas de demostración

| Rol | Correo | Contraseña |
|---|---|---|
| Administrador | `admin@dartpizza.local` | `Admin123!` |
| Empleado | `empleado@dartpizza.local` | `Empleado123!` |
| Cliente | `cliente@dartpizza.local` | `Cliente123!` |

Cambia las contraseñas y el secreto de firma antes de usarlo con datos reales. Los datos incluidos son demostrativos.

## Direcciones útiles

- Aplicación: http://127.0.0.1:8000
- Documentación interactiva de la API: http://127.0.0.1:8000/docs
- Estado del servidor: http://127.0.0.1:8000/api/health

## Configuración

Variables opcionales:

- `DART_DB`: ruta del archivo SQLite. Por defecto `data/dartpizza.db`.
- `JWT_SECRET`: secreto de firma de tokens. Define uno aleatorio y privado antes de despliegue.

Ejemplo PowerShell:

```powershell
$env:JWT_SECRET = "REEMPLAZA_ESTO_POR_UN_SECRETO_LARGO_Y_ALEATORIO"
```

## Alcance y limitaciones conocidas

Esta es una base funcional local/MVP, no una certificación de producción. El módulo de IA actual hace cálculos y recomendaciones determinísticas sobre los registros reales; **no es un modelo de aprendizaje automático ni un chatbot LLM**. No se activa Ollama ni un proveedor externo. No se implementaron todavía MFA, recuperación/verificación de correo, pasarela de pagos, notificaciones push, exportación PDF/Excel, administración avanzada de permisos, recetas con descuento automático de ingredientes, ni predicción estadística fiable. Las funciones no implementadas no se presentan como si lo estuvieran.

El cambio de estado de pedido es operativo; en una futura fase debe incorporarse un flujo de transiciones validado, cancelaciones con reversión de stock y control transaccional de inventario de recetas. Los endpoints usan SQLite y están pensados para pruebas y operación local de demostración. Antes de exponerlo a internet se requiere endurecimiento de seguridad, HTTPS, gestión de secretos, política de sesiones, copias de seguridad, pruebas de carga y revisión de privacidad conforme a la Ley 1581 de 2012.

## Estructura

```text
DartPizzaAI/
├── app/
│   ├── main.py              # API, autenticación, persistencia y reglas
│   └── static/              # Interfaz web responsive
├── data/                    # Base SQLite creada al iniciar
├── tests/                   # Pruebas de humo
├── requirements.txt
├── INICIAR_DART_PIZZA.bat
└── README.md
```
