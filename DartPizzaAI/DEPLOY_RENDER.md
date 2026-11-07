# Despliegue de Dart Pizza AI en Render

## Antes de empezar

Esta versión utiliza SQLite. El servicio Render debe tener un disco persistente montado en `/var/data`; el archivo de base de datos queda en `/var/data/dartpizza.db`. Los discos persistentes requieren un plan de servicio de pago en Render. No cambies a una instancia efímera/free sin migrar antes a una base de datos administrada: perderías los datos al reiniciar o desplegar.

## Publicación

1. Crea una cuenta en https://render.com/.
2. Sube el contenido de esta carpeta a un repositorio **privado** de GitHub.
3. En Render selecciona **New + → Blueprint** y conecta ese repositorio.
4. Render leerá `render.yaml` y propondrá crear el servicio `dart-pizza-ai` con disco persistente.
5. Al solicitar las variables secretas, introduce:
   - `ADMIN_EMAIL`: correo que usarás como administrador.
   - `ADMIN_PASSWORD`: contraseña única de al menos 12 caracteres. No reutilices la contraseña de otros servicios.
6. Confirma la creación. Espera a que el despliegue termine.
7. Abre la URL `https://dart-pizza-ai.onrender.com` que Render asigna (el nombre puede variar si ya está ocupado).
8. Comprueba `https://TU-DOMINIO/api/health` y luego inicia sesión con el correo y contraseña que configuraste.

## Seguridad y operación

- No subas `.env`, contraseñas, tokens ni datos reales al repositorio.
- `JWT_SECRET` se genera automáticamente por el Blueprint.
- La configuración cloud desactiva los usuarios demo inseguros y crea un único administrador inicial a partir de `ADMIN_EMAIL` y `ADMIN_PASSWORD`.
- Conserva el disco persistente y configura copias de seguridad antes de operar con pedidos reales.
- No elimines ni recrees el disco: contiene la base de datos.
- Configura un dominio propio desde Render cuando estés listo.
- Para uso comercial, recomendamos migrar SQLite a PostgreSQL administrado, habilitar copias de seguridad verificadas y completar una auditoría de seguridad.

## Limitación

Este despliegue publica el MVP actual; no agrega por sí solo pasarela de pagos, MFA, predicción ML ni un LLM. El panel de inteligencia utiliza consultas y reglas determinísticas sobre los pedidos almacenados.
