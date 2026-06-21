# Guión de Vídeo — Despliegue v3 desde Cero en Azure

> Cubre el despliegue completo del servicio final (Frontend + Backend + persistencia en Azure Files) partiendo de una suscripción de Azure vacía. Todos los comandos están listos para copiar y pegar en PowerShell.

---

## Escena 1 — Introducción (≈1 min)

**Narración:** Presentar brevemente el proyecto: una API GenAI en FastAPI con una arquitectura de dos contenedores (Frontend y Backend) enrutados y comunicados internamente. Explicar que realizaremos el despliegue completo desde cero en Microsoft Azure utilizando los siguientes componentes clave:
* **Grupo de Recursos (Resource Group):** Contenedor lógico para administrar de manera unificada todos los servicios del despliegue.
* **Azure Container Registry (ACR):** Registro privado de Docker donde compilaremos y almacenaremos las imágenes de nuestros contenedores Frontend y Backend.
* **Plan de App Service (App Service Plan):** La infraestructura de cómputo Linux (SKU B1) sobre la cual se ejecutarán nuestros contenedores.
* **Azure App Service (Web App for Containers):** El servicio PaaS multi-contenedor donde desplegaremos nuestro archivo `docker-compose.yml`.
* **Cuenta de Almacenamiento (Storage Account):** El almacén general en la nube necesario para dar soporte al almacenamiento persistente.
* **Azure Files (File Share):** El recurso compartido de archivos que montaremos como volumen persistente en el contenedor de Frontend para salvaguardar el archivo `history.txt` con los logs de comunicación.

**Pantalla:** Mostrar el diagrama de arquitectura final (`images/26_diagrama_arquitectura_v3.png`) señalando cada uno de estos componentes a medida que se mencionan:

![Diagrama de Arquitectura Final](images/26_diagrama_arquitectura_v3.png)

---

## Escena 2 — Prerrequisitos (≈1 min)

**Narración:** Verificar que Docker Desktop está arrancado y que Azure CLI está instalado.

**Pantalla / comandos:**
```powershell
docker info        # verificar Docker Desktop activo
az --version       # verificar Azure CLI instalado
```

> ⚠️ Si Docker Desktop no está corriendo, iniciarlo con:
> `Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"`
> Esperar al mensaje *"Docker Desktop is running"* en la barra de tareas antes de continuar.

---

## Escena 3 — Login y definición de variables (≈2 min)

**Narración:** Autenticarse en Azure y definir las variables de entorno que se usarán en todos los pasos siguientes.

```powershell
# Autenticarse en Azure
az login

# Definir variables de entorno para los comandos
$RESOURCE_GROUP  = "gruporecursosia"
$LOCATION        = "spaincentral"
$ACR_NAME        = "planservicioia"
$APP_SERVICE_PLAN = "plan-fastapi-gemini"
$WEB_APP_NAME    = "webapp-fastapi-gemini"
$STORAGE_ACCOUNT = "almacenamientoappia"
$SHARE_NAME      = "archivos-texto"
$MOUNT_PATH      = "/app/data"

# Leer la API Key de Gemini desde el archivo .env (evita exponer la clave en el historial de comandos)
$GEMINI_API_KEY = (Get-Content .env | Select-String "GEMINI_API_KEY" | ForEach-Object { $_.ToString().Split("=",2)[1] })
```

---

## Escena 4 — Creación del Grupo de Recursos y ACR (≈2 min)

**Narración:** Crear el grupo de recursos y el registro privado de contenedores (ACR). Habilitar el usuario administrador y autenticarse desde Docker local.

```powershell
# Crear el grupo de recursos
az group create --name $RESOURCE_GROUP --location $LOCATION

# Crear el Azure Container Registry (SKU básico para desarrollo/pruebas)
az acr create --name $ACR_NAME --resource-group $RESOURCE_GROUP --sku Basic

# Habilitar usuario admin del registro
az acr update -n $ACR_NAME --admin-enabled true

# Obtener la contraseña de administrador
$ACR_PASSWORD = (az acr credential show --name $ACR_NAME --query "passwords[0].value" -o tsv)

# Iniciar sesión local en Docker con las credenciales de ACR (usando password-stdin por seguridad)
echo $ACR_PASSWORD | docker login "$ACR_NAME.azurecr.io" --username $ACR_NAME --password-stdin
```

---

## Escena 5 — Creación del Storage Account y File Share (≈2 min)

**Narración:** Crear la cuenta de almacenamiento y el recurso compartido de Azure Files donde el Frontend guardará el historial de logs de forma persistente.

```powershell
# 1. Crear la Cuenta de Almacenamiento (Storage Account)
az storage account create --name $STORAGE_ACCOUNT --resource-group $RESOURCE_GROUP --location $LOCATION --sku Standard_LRS

# 2. Crear el recurso compartido de archivos (File Share)
az storage share-rm create --resource-group $RESOURCE_GROUP --storage-account $STORAGE_ACCOUNT --name $SHARE_NAME --quota 5
```

---

## Escena 6 — Build y Push de las imágenes v3 (≈3 min)

**Narración:**
* Si observamos los archivos `Dockerfile` (tanto en el **Backend** como en el **Frontend**), destacamos:
  * El uso de la imagen base ligera `python:3.11-slim` para minimizar el tamaño final de las imágenes.
  * El orden de las instrucciones: se copia primero `requirements.txt` e instalan dependencias antes de copiar el código de la aplicación. Esto aprovecha la caché de capas de Docker, evitando reinstalar librerías en futuros builds si no cambian las dependencias.
  * El puerto expuesto: el Backend expone el puerto `8080` y el Frontend el puerto `80` (para tráfico HTTP público).
* Del archivo `docker-compose.yml`, destacamos:
  * La definición de los nombres de las imágenes utilizando el prefijo de nuestro ACR (`planservicioia.azurecr.io/fastapi-...`), lo cual nos permite compilar y subir directamente las imágenes a Azure con comandos nativos de docker-compose.
  * El aislamiento de red: el Backend usa `expose` en el puerto `8080` (solo visible internamente), mientras que el Frontend mapea `ports: 80:80` (expuesto al exterior).
  * La inyección de variables de entorno, como la clave de Gemini en el backend y la `BACKEND_URL` en el frontend apuntando a `http://backend:8080` para resolución de DNS en local.
  * El volumen persistente llamado `AlmacenamientoPersistente` montado en la ruta `/app/data` del Frontend para conservar el archivo de logs `history.txt`.

Procedemos a compilar y subir las imágenes al ACR.

**Pantalla:** Mostrar el código de `backend/Dockerfile`, `frontend/Dockerfile` y `docker-compose.yml`. Luego, ejecutar en consola:

```powershell
# Construimos ambas imágenes
docker-compose build

# Subimos las imágenes a Azure Container Registry
docker-compose push
```

---

## Escena 7 — Creación del App Service Plan y Web App (≈3 min)

**Narración:** Aprovisionar el plan de hospedaje Linux y crear la Web App en modo multi-contenedor, pasándole directamente el `docker-compose.yml`.

```powershell
# Crear el Plan de App Service (SKU B1 de Linux como nivel básico de desarrollo)
az appservice plan create --name $APP_SERVICE_PLAN --resource-group $RESOURCE_GROUP --sku B1 --is-linux

# Crear la Web App pasándole el docker-compose.yml directamente
az webapp create --resource-group $RESOURCE_GROUP --plan $APP_SERVICE_PLAN --name $WEB_APP_NAME --multicontainer-config-type compose --multicontainer-config-file docker-compose.yml
```

---

## Escena 8 — Configuración de credenciales y variables de entorno (≈2 min)

**Narración:** Vincular el ACR a la Web App para que pueda descargar las imágenes, y configurar los secretos y parámetros de red necesarios.

```powershell
# Reconectar las credenciales del ACR a la Web App (usando parámetros actualizados)
az webapp config container set --name $WEB_APP_NAME --resource-group $RESOURCE_GROUP `
  --container-registry-url "https://$ACR_NAME.azurecr.io" `
  --container-registry-user $ACR_NAME `
  --container-registry-password $ACR_PASSWORD

# Configurar variables de entorno (la API Key se lee del .env, no aparece en el comando)
az webapp config appsettings set --resource-group $RESOURCE_GROUP --name $WEB_APP_NAME `
  --settings GEMINI_API_KEY=$GEMINI_API_KEY WEBSITES_PORT=80 BACKEND_URL="http://localhost:8080"
```

> ⚠️ En Azure App Service Multi-container, los contenedores comparten el mismo espacio de red, por eso el Frontend llama al Backend por `http://localhost:8080` en lugar de `http://backend:8080`.

---

## Escena 9 — Montaje del almacenamiento persistente (≈2 min)

**Narración:** Obtener la clave del Storage Account y montar el File Share en la ruta `/app/data` del contenedor Frontend.

```powershell
# 1. Obtener la clave de acceso del Storage Account
$STORAGE_KEY = (az storage account keys list --resource-group $RESOURCE_GROUP --account-name $STORAGE_ACCOUNT --query "[0].value" --output tsv)

# 2. (Opcional) Eliminar un montaje previo con el mismo ID si existe
az webapp config storage-account delete --resource-group $RESOURCE_GROUP --name $WEB_APP_NAME --custom-id AlmacenamientoPersistente

# 3. (Opcional) Limpiar el historial previo en la nube para empezar con una demo limpia (si no existe el archivo, dará error, el cual se puede ignorar)
az storage file delete --share-name $SHARE_NAME --account-name $STORAGE_ACCOUNT --account-key $STORAGE_KEY --path history.txt

# 4. Montar el almacenamiento persistente en la Web App
az webapp config storage-account add --resource-group $RESOURCE_GROUP --name $WEB_APP_NAME `
  --custom-id AlmacenamientoPersistente --storage-type AzureFiles `
  --account-name $STORAGE_ACCOUNT --share-name $SHARE_NAME `
  --access-key $STORAGE_KEY --mount-path $MOUNT_PATH
```

---

## Escena 10 — Arranque y verificación (≈3 min)

**Narración:** Arrancar la webapp, esperar el inicio de los contenedores (~2 minutos) y verificar que el endpoint `/generate` responde de forma exitosa. Posteriormente, consultar el endpoint `/logs` para comprobar las trazas registradas, lo cual **demuestra la interconexión y comunicación directa de red interna entre ambos contenedores** (Frontend llamando al Backend).

```powershell
# Iniciar la Web App
az webapp start --name $WEB_APP_NAME --resource-group $RESOURCE_GROUP
```

> ⏳ Esperar ~2 minutos a que los contenedores arranquen.
> ⚠️ **Nota:** Si la primera petición de generación devuelve un error como `"All connection attempts failed"`, es normal porque el backend aún está iniciando. Espera un momento y vuelve a intentarlo.

```powershell
# Probar el endpoint de generación de contenido
Invoke-WebRequest "https://webapp-fastapi-gemini.azurewebsites.net/generate?prompt=Azure_Prompt_v3" -UseBasicParsing

# Comprobar los logs de comunicación Frontend -> Backend
(Invoke-WebRequest "https://webapp-fastapi-gemini.azurewebsites.net/logs" -UseBasicParsing).Content

# Verificar que el archivo de logs se ha creado físicamente en el almacenamiento de Azure Files
az storage file list --share-name $SHARE_NAME --account-name $STORAGE_ACCOUNT --account-key $STORAGE_KEY --output table

# (Opcional) Descargar y mostrar el contenido directo de history.txt desde la nube
az storage file download --share-name $SHARE_NAME --account-name $STORAGE_ACCOUNT --account-key $STORAGE_KEY --path history.txt --dest .
Get-Content history.txt
Remove-Item history.txt
```

**Salida esperada de `/generate`:**
```json
{"prompt": "Azure_Prompt_v3", "text": "...respuesta de Gemini..."}
```

**Salida esperada de `/logs`:**
```json
{"logs": ["2026-06-21 ... INFO - Enviando prompt al servicio B en la URL http://localhost:8080/generate", "2026-06-21 ... INFO - Respuesta exitosa recibida del servicio B."]}
```

---

## Escena 11 — Prueba de persistencia (≈2 min)

**Narración:** Forzar un reinicio de la webapp para simular un fallo o redepliegue y comprobar que el historial de logs sigue presente en Azure Files.

```powershell
# Forzar reinicio de la Web App
az webapp restart --name $WEB_APP_NAME --resource-group $RESOURCE_GROUP
```

> ⏳ Esperar ~2 minutos el arranque y consultar de nuevo los logs:

```powershell
(Invoke-WebRequest "https://webapp-fastapi-gemini.azurewebsites.net/logs" -UseBasicParsing).Content
```

**Resultado esperado:** Los registros de la escena anterior siguen presentes → la persistencia en Azure Files funciona correctamente.

---

## Escena 12 — Cierre (≈1 min)

**Narración:** Resumen de lo demostrado: dos contenedores coordinados por Docker Compose, desplegados en Azure App Service (PaaS), con comunicación interna vía `localhost` y persistencia en Azure Files.

**Pantalla:** Mostrar las URLs en vivo en el navegador:
- [`https://webapp-fastapi-gemini.azurewebsites.net/generate?prompt=Demo_Final`](https://webapp-fastapi-gemini.azurewebsites.net/generate?prompt=Demo_Final)
- [`https://webapp-fastapi-gemini.azurewebsites.net/logs`](https://webapp-fastapi-gemini.azurewebsites.net/logs)

---

## Escena 13 — Control de Gastos y Limpieza (≈1 min)

**Narración:** Por último, para evitar que el despliegue siga consumiendo créditos de estudiante de Azure, podemos pausar los contenedores deteniendo la Web App, o bien eliminar el grupo de recursos por completo si ya hemos finalizado la práctica.

```powershell
# Opción A: Detener la Web App (pausa la ejecución de los contenedores sin borrar la configuración)
az webapp stop --name $WEB_APP_NAME --resource-group $RESOURCE_GROUP

# Opción B: Eliminar el Grupo de Recursos completo (borra absolutamente todo y detiene el 100% del consumo)
az group delete --name $RESOURCE_GROUP --yes --no-wait
```
