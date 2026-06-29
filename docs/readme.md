# Práctica PaaS: Despliegue de Servicio GenAI en Azure App Service (Rama Mínimo)

Este documento detalla la estructura, generación de imagen y flujo de comandos para realizar el despliegue del servicio mínimo en **Azure App Service (PaaS)** sobre Linux. El servicio consiste en un único contenedor que expone una API desarrollada en **FastAPI** que conecta con la API de **Gemini** para procesar prompts de usuario.

---

## Componentes Azure Necesarios

Para llevar a cabo el despliegue de esta arquitectura en la nube, se requieren los siguientes componentes de **Microsoft Azure**:

* **Grupo de Recursos (Resource Group):** Contenedor lógico que agrupa todos los recursos relacionados con este despliegue para facilitar su administración y eliminación conjunta.
* **Azure Container Registry (ACR):** Registro privado de Docker en Azure donde se compilan, almacenan y gestionan las imágenes de los contenedores (`backend` y `frontend`).
* **Plan de App Service (App Service Plan):** Define los recursos físicos de computación y el sistema operativo (Linux con SKU B1) sobre los que correrá la aplicación.
* **Azure App Service (Web App for Containers):** Servicio PaaS que ejecuta la aplicación web a partir de la configuración multi-contenedor definida en el archivo `docker-compose.yml`.
* **Cuenta de Almacenamiento (Storage Account):** Servicio que aloja y gestiona las capacidades de almacenamiento en la nube requeridas para el proyecto.
* **Azure Files (File Share):** Recurso compartido de archivos montado como volumen persistente en la Web App (mapeado a `/app/data`) para salvaguardar el archivo de logs `history.txt` y asegurar su persistencia tras reinicios de los contenedores.

---

## URLs del Servicio Desplegado en Azure

> **ℹ️ Nota:** Todos los bloques de este documento comparten la misma Web App de Azure (`webapp-fastapi-gemini`), actualizándose iterativamente. La URL base es única y permanece constante a través de las distintas versiones desplegadas.

| Endpoint | URL | Descripción |
|---|---|---|
| Generación de contenido | [`https://webapp-fastapi-gemini.azurewebsites.net/generate?prompt=...`](https://webapp-fastapi-gemini.azurewebsites.net/generate?prompt=Hello) | Envía un prompt a Gemini y devuelve la respuesta |
| Historial de logs | [`https://webapp-fastapi-gemini.azurewebsites.net/logs`](https://webapp-fastapi-gemini.azurewebsites.net/logs) | Devuelve el historial de comunicaciones Frontend→Backend (disponible desde Bloque 4) |

---

## Descripción de los Despliegues

La práctica implementa un servicio de Inteligencia Artificial Generativa (GenAI) basado en la API de **Google Gemini**, desplegado de forma iterativa en **Azure App Service (PaaS)** a través de cuatro bloques de complejidad creciente:

| Bloque | Tipo | Descripción resumida |
|---|---|---|
| **1** | Contenedor único | Una sola imagen FastAPI que recibe prompts del usuario y los envía directamente a la API de Gemini. Sin persistencia, sin proxy. Se despliega en Azure App Service (Linux) usando Azure Container Registry (ACR). |
| **2** | Docker Compose — 2 contenedores | Se divide en un **Frontend** (gateway público en puerto 80) y un **Backend** (procesador Gemini en puerto 8080, sin exposición directa al exterior). El Frontend enruta las peticiones al Backend internamente. Despliegue multi-contenedor en Azure App Service. |
| **3** | Compose + Persistencia (backend) | Sobre el Bloque 2, el Backend guarda cada prompt en un archivo `history.txt` montado sobre **Azure Files** (File Share). El historial sobrevive a reinicios y reempliegues gracias al volumen persistente. |
| **4** | Compose + Persistencia (frontend) + Logs | El Frontend pasa a ser el responsable de registrar logs de comunicación (URL llamada, respuesta recibida) en `history.txt`. El volumen persistente se traslada al Frontend. Se añade el endpoint `/logs` para consultar el historial. Es la arquitectura final desplegada. |

Todos los bloques utilizan imágenes propias construidas desde cero (no se usa DockerHub) y almacenadas en el **Azure Container Registry** `planservicioia.azurecr.io`.

---

## Prerrequisitos del Entorno

Antes de comenzar a ejecutar los comandos de despliegue o pruebas locales, asegúrate de contar con los siguientes elementos instalados y configurados en tu equipo:

### 1. Docker Desktop
* **Uso:** Construcción, etiquetado y ejecución de contenedores locales, así como publicación de imágenes en el registro privado.
* **Instalación:** Descarga e instala [Docker Desktop para Windows](https://www.docker.com/products/docker-desktop/).
* **Verificación:** Ejecuta el siguiente comando en PowerShell para verificar que el servicio está activo:
  ```powershell
  docker info
  ```

  ![Verificación de Docker Desktop](images/00_docker.png)

* **Inicio rápido (si no está activo):** Si Docker no se está ejecutando, puedes iniciarlo desde el menú de inicio de Windows o por PowerShell:
  ```powershell
  Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
  ```
  *Espera a que el icono de Docker en la barra de tareas muestre "Docker Desktop is running" antes de continuar.*

### 2. Azure CLI
* **Uso:** Administración, creación y configuración de toda la infraestructura PaaS (Azure App Service, Azure Container Registry, Azure Files).
* **Instalación:** Sigue la [guía de instalación de Azure CLI para Windows](https://learn.microsoft.com/cli/azure/install-azure-cli-windows).
* **Verificación:** Ejecuta el siguiente comando en PowerShell para confirmar que está instalado correctamente:
  ```powershell
  az --version
  ```

  ![Verificación de Azure CLI](images/00_az.png)

---

## Bloque 1: Despliegue de un Contenedor

### 1.1. Descripción del Despliegue (Arquitectura Mínima)

> 📦 **Código de la primera versión:** El código fuente correspondiente a este Bloque 1 está disponible en el [Release v1 de GitHub](https://github.com/danielquinti/azure-assignment/releases/tag/v1).

El despliegue consiste en un servicio web gestionado en contenedor dentro de la plataforma **Azure App Service (Linux Web App)**. 

### Características del despliegue:
* **Sin Persistencia:** El contenedor funciona bajo el principio de infraestructura efímera (stateless). Las solicitudes se procesan en tiempo real y no se guarda historial de las consultas en archivos locales ni bases de datos.
* **Único Contenedor:** Toda la lógica reside en una sola aplicación de FastAPI, eliminando la necesidad de proxies o bases de datos adicionales.
* **Integración GenAI:** Se conecta directamente con la API oficial de Google Gemini usando el SDK de nueva generación (`google-genai`) y la clave de API `GEMINI_API_KEY` inyectada mediante variables de entorno en la nube.
* **Infraestructura PaaS:** Se emplea un plan de App Service en Linux, ideal para albergar APIs basadas en contenedores con escalado automático de recursos.

![Diagrama de Secuencia - Arquitectura Mínima v1](images/01_diagrama_arquitectura_v1.png)

---

### 1.2. Definición del Contenedor (Dockerfile)

La imagen se construye a partir del siguiente `Dockerfile`, el cual optimiza el peso de la imagen mediante la versión `slim` de Python y aprovecha la caché de capas de Docker copiando primero las dependencias.

```dockerfile
# Use official Python slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements.txt first to leverage Docker cache
COPY requirements.txt .

# Install all dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the FastAPI app
COPY app.py .

# Expose FastAPI port
EXPOSE 8080

# Run the app with Uvicorn
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
```

#### Código de la Aplicación (`app.py`):
El servicio expone un único endpoint `/generate` que interactúa de manera asíncrona con el modelo `gemini-2.5-flash`:

```python
# app_fastapi_prompt.py
from dotenv import load_dotenv
from fastapi import FastAPI, Query, HTTPException
from google import genai
import os

# Carga variables de entorno locales (si existen)
load_dotenv()
client = genai.Client()

app = FastAPI()

@app.get("/generate")
async def generate_content(prompt: str = Query(..., description="The prompt to send to Gemini")):
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return {"prompt": prompt, "text": response.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

### 1.3. Pruebas y Validación en Local

Antes de proceder con el despliegue en la nube, se recomienda validar el correcto funcionamiento de la aplicación de manera local mediante Docker.

> **⚠️ Prerequisito:** Asegúrate de que **Docker Desktop** está arrancado antes de ejecutar cualquier comando `docker`. Puedes iniciarlo desde el menú de inicio de Windows o ejecutando `Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"` en PowerShell. Espera a que el icono de Docker en la barra de tareas muestre el mensaje *"Docker Desktop is running"* antes de continuar.

#### Ejecución mediante Docker local
Construye la imagen localmente y levanta el contenedor pasando la variable de entorno (para ejecución directa sin Docker, existe un archivo `.env` en la raíz del proyecto con la clave `GEMINI_API_KEY`):

```powershell
# Leer la API Key desde el archivo .env (evita exponer la clave en el historial de comandos)
$env:GEMINI_API_KEY = (Get-Content .env | Select-String "GEMINI_API_KEY" | ForEach-Object { $_.ToString().Split("=",2)[1] })

# Construir la imagen local
docker build -t fastapi-gemini:local .

# Ejecutar el contenedor
docker run -d -p 8080:8080 --name fastapi-app-local -e GEMINI_API_KEY=$env:GEMINI_API_KEY fastapi-gemini:local
```

![Arranque de contenedor único](images/02_arranque_contenedor_unico.png)

#### Verificación local:
Realiza una llamada de prueba desde el navegador o consola al puerto local `8080`:

```powershell
Invoke-WebRequest "http://localhost:8080/generate?prompt=Hello_Local_Testing" -UseBasicParsing
```

> **ℹ️ Nota sobre PowerShell:** Se añade el parámetro `-UseBasicParsing` en todos los comandos `Invoke-WebRequest` de esta práctica para evitar que PowerShell intente inicializar el motor de Internet Explorer (lo cual suele lanzar una advertencia de seguridad interactiva y requerir confirmación del usuario para continuar).

![Prueba local exitosa](images/02_prueba_local_contenedor_unico.png)

---

### 1.4. Guía de Pasos Realizados (Despliegue en Azure)

A continuación se presenta la secuencia completa de comandos ejecutados en la consola para registrar la imagen de contenedor y aprovisionar la infraestructura en Azure.

#### Paso 1: Autenticación en Azure
Inicia sesión en tu suscripción de Azure mediante CLI. Al ejecutar este comando, se abrirá automáticamente un diálogo en el sistema operativo para que inicies sesión con tus credenciales de Azure. Cuando termines el proceso de autenticación, tendrás que seleccionar la suscripción. Pulsa "Enter" en la consol para continuar con el predeterminado.

```powershell
# Autenticarse en Azure
az login
```

![Autenticación en Azure](images/03_login.png)

#### Paso 2: Definición de variables de entorno
Define las variables de entorno de trabajo en tu sesión de PowerShell para utilizarlas en los siguientes comandos:

```powershell
# Definir variables de entorno para los comandos
$RESOURCE_GROUP = "gruporecursosia"
$LOCATION = "spaincentral"
$ACR_NAME = "planservicioia"
$APP_SERVICE_PLAN = "plan-fastapi-gemini"
$WEB_APP_NAME = "webapp-fastapi-gemini"
$IMAGE_TAG = "planservicioia.azurecr.io/fastapi-gemini:v1"
# Leer la API Key desde el archivo .env
$GEMINI_API_KEY = (Get-Content .env | Select-String "GEMINI_API_KEY" | ForEach-Object { $_.ToString().Split("=",2)[1] })
```

![Definición de variables de entorno](images/03_variables.png)

#### Paso 3: Creación del Grupo de Recursos y del Azure Container Registry (ACR)
Crea un grupo de recursos donde se alojarán todos los componentes y aprovisiona el registro de contenedores privado:

```powershell
# Crear el grupo de recursos
az group create --name $RESOURCE_GROUP --location $LOCATION
```

![Grupo de Recursos](images/03_creacion_grupo_recursos.png)

```powershell
# Crear el Azure Container Registry (SKU básico para desarrollo/pruebas)
az acr create --name $ACR_NAME --resource-group $RESOURCE_GROUP --sku Basic
```

![Azure Container Registry](images/04_creacion_acr.png)

#### Paso 4: Habilitar usuario administrador en ACR y autenticarse localmente
Habilita el acceso de administrador para obtener las credenciales de lectura/escritura de imágenes directamente desde Docker:

```powershell
# Habilitar usuario admin del registro
az acr update -n $ACR_NAME --admin-enabled true
```

![Habilitar Administrador ACR](images/05_habilitar_admin_acr.png)

```powershell
# Obtener la contraseña de administrador
$ACR_PASSWORD = (az acr credential show --name $ACR_NAME --query "passwords[0].value" -o tsv)

# Iniciar sesión local en Docker con las credenciales de ACR (usando password-stdin por seguridad)
echo $ACR_PASSWORD | docker login "$ACR_NAME.azurecr.io" --username $ACR_NAME --password-stdin
```

![Autenticación Docker local](images/06_login_docker_acr.png)

#### Paso 5: Construcción y subida de la imagen Docker
Construye la imagen Docker localmente etiquetándola con la URI del registro de Azure, y súbela al repositorio:

```powershell
# Construir la imagen usando el Dockerfile de la raíz
docker build -t $IMAGE_TAG .
```

![Construcción de la imagen Docker](images/07_build_imagen_docker.png)

```powershell
# Subir la imagen a Azure Container Registry
docker push $IMAGE_TAG
```

![Subida de la imagen a ACR](images/08_push_imagen_acr.png)

#### Paso 6: Creación del Plan de App Service
Aprovisiona un plan de hospedaje en Azure App Service configurado en Linux:

```powershell
# Crear el Plan de App Service (SKU B1 de Linux como nivel básico de desarrollo)
az appservice plan create --name $APP_SERVICE_PLAN --resource-group $RESOURCE_GROUP --sku B1 --is-linux
```

![Creación del Plan de App Service](images/09_creacion_plan_appservice.png)

#### Paso 7: Despliegue de la Web App desde el ACR
Aprovisiona la Web App de contenedores configurando la imagen previamente cargada en el registro de Azure:

```powershell
# Crear la Web App con la imagen del contenedor de Azure
az webapp create --resource-group $RESOURCE_GROUP --plan $APP_SERVICE_PLAN --name $WEB_APP_NAME --container-image-name $IMAGE_TAG
```

![Creación de la Web App en Azure](images/10_creacion_webapp_azure.png)

#### Paso 8: Configuración de Credenciales de Registro y Variables de Entorno
Configura la autenticación del App Service contra el ACR para que pueda descargar las actualizaciones de la imagen y define los secretos de la aplicación:

```powershell

# Vincular las credenciales del registro privado a la Web App (usando parámetros actualizados)
az webapp config container set --name $WEB_APP_NAME --resource-group $RESOURCE_GROUP --container-image-name $IMAGE_TAG --container-registry-url "https://$ACR_NAME.azurecr.io" --container-registry-user $ACR_NAME --container-registry-password $ACR_PASSWORD

# Definir la API Key de Gemini y forzar el puerto 8080 dentro del contenedor
az webapp config appsettings set --resource-group $RESOURCE_GROUP --name $WEB_APP_NAME --settings WEBSITES_PORT=8080 GEMINI_API_KEY=$GEMINI_API_KEY
```

![Configuración de la Web App en Azure](images/11_configuracion_webapp_azure.png)

---

### 1.5. Verificación del Funcionamiento en Azure

Una vez que el despliegue haya completado su inicio en Azure, puedes probar el endpoint de generación ejecutando la siguiente llamada HTTP desde la consola:

```powershell
# Realizar petición de prueba a la API desplegada en Azure
Invoke-WebRequest "https://$WEB_APP_NAME.azurewebsites.net/generate?prompt=Explain_PaaS_in_one_sentence" -UseBasicParsing

Invoke-WebRequest "https://webapp-fastapi-gemini.azurewebsites.net/generate?prompt=Explain_PaaS_in_one_sentence" -UseBasicParsing
```

#### Formato esperado de respuesta:
```json
{
  "prompt": "Explain_PaaS_in_one_sentence",
  "text": "Platform as a Service (PaaS) is a cloud computing model where a third-party provider delivers hardware and software tools—usually those needed for application development—to users over the internet."
}
```

![Verificación de la API en Azure](images/12_verificacion_api_azure_v1.png)

## Bloque 2: Despliegue Docker Compose con Dos Contenedores

En esta segunda iteración, la aplicación se estructura en una arquitectura de múltiples contenedores coordinados por Docker Compose. Esta arquitectura divide el monolito en:
1. **Frontend API (Gateway):** Un contenedor FastAPI en el puerto 80 que recibe todas las peticiones externas y las redirige hacia la capa interna.
2. **Backend API:** El contenedor FastAPI original en el puerto 8080 que se comunica exclusivamente con la API de Gemini, protegido del exterior.

### 2.1. Estructura de Docker Compose

En la raíz del proyecto se ha introducido un archivo `docker-compose.yml` que orquesta ambos servicios. Este archivo ya cuenta con el nombre y URL de su ACR resueltos directamente en las imágenes, por lo que no requiere sustitución dinámica de variables:

```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    image: planservicioia.azurecr.io/fastapi-backend:v1
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
    expose:
      - "8080"

  frontend:
    build: ./frontend
    image: planservicioia.azurecr.io/fastapi-frontend:v1
    environment:
      - BACKEND_URL=http://backend:8080
    ports:
      - "80:80"
    depends_on:
      - backend
```

### 2.2. Pruebas Locales (Docker Compose)

En lugar de construir una sola imagen, utiliza compose para levantar el clúster entero simultáneamente:

> **⚠️ Prerequisito:** Comprueba que **Docker Desktop** está en ejecución antes de continuar (icono en la barra de tareas → *"Docker Desktop is running"*).

```powershell
# Leer la API Key desde el archivo .env
$env:GEMINI_API_KEY = (Get-Content .env | Select-String "GEMINI_API_KEY" | ForEach-Object { $_.ToString().Split("=",2)[1] })
```

![API Key leída localmente](images/13_gemini_compose.png)

```powershell
# Construir y levantar los dos contenedores
docker-compose up --build -d
```
Verifique apuntando al puerto 80 (el cual ahora es gestionado por el Gateway frontend):
```powershell
Invoke-WebRequest "http://localhost:80/generate?prompt=Prueba_Compose"
```

![Prueba local con Docker Compose](images/13_prueba_local_docker_compose.png)

### 2.3. Despliegue en Azure App Service Multi-Container

Para desplegar la aplicación en Azure usando esta topología, los comandos a ejecutar cambian ligeramente. Si has iniciado una nueva sesión de terminal, redefine primero las variables necesarias:

```powershell
$RESOURCE_GROUP   = "gruporecursosia"
$LOCATION         = "spaincentral"
$ACR_NAME         = "planservicioia"
$APP_SERVICE_PLAN = "plan-fastapi-gemini"
$WEB_APP_NAME     = "webapp-fastapi-gemini"
$ACR_PASSWORD     = (az acr credential show --name $ACR_NAME --query "passwords[0].value" -o tsv)
```

![Variables de entorno cargadas para compose](images/13_variable_compose.png)

**A. Construcción y subida de ambas imágenes al ACR**
```powershell
# Exportamos el nombre del ACR para los tags del Compose
$env:ACR_NAME=$ACR_NAME

# Autenticarse en el ACR antes de hacer push
docker login "$ACR_NAME.azurecr.io" --username $ACR_NAME --password $ACR_PASSWORD
```

![Autenticación en el ACR para Compose](images/13_acr_compose.png)

```powershell
# Construimos y subimos las imágenes
docker-compose build
docker-compose push
```

![docker-compose build](images/14_build_imagenes_compose.png)
![docker-compose push](images/15_push_imagenes_compose.png)


**B. Aprovisionamiento de la Web App en modo Multi-Container**
```powershell
# Crear el App Service Plan (si no lo tienes creado del ejercicio anterior)
az appservice plan create --name $APP_SERVICE_PLAN --resource-group $RESOURCE_GROUP --sku B1 --is-linux

# Crear la Web App pasándole el docker-compose.yml directamente
az webapp create --resource-group $RESOURCE_GROUP --plan $APP_SERVICE_PLAN --name $WEB_APP_NAME --multicontainer-config-type compose --multicontainer-config-file docker-compose.yml
```

![Creación del Plan de App Service](images/16_creacion_plan_appservice_compose.png)
![Creación de la Web App Multi-Contenedor](images/17_creacion_webapp_multicontenedor.png)

**C. Configuración de Variables en Azure**
```powershell
# Vincular las credenciales del ACR a la Web App (usando parámetros actualizados)
az webapp config container set --name $WEB_APP_NAME --resource-group $RESOURCE_GROUP --container-registry-url "https://$ACR_NAME.azurecr.io" --container-registry-user $ACR_NAME --container-registry-password $ACR_PASSWORD

# Leer la API Key desde el archivo .env
$GEMINI_API_KEY = (Get-Content .env | Select-String "GEMINI_API_KEY" | ForEach-Object { $_.ToString().Split("=",2)[1] })

# Definir la API Key de Gemini
az webapp config appsettings set --resource-group $RESOURCE_GROUP --name $WEB_APP_NAME --settings GEMINI_API_KEY=$GEMINI_API_KEY

# Configurar el puerto público: Indicamos a Azure que envíe el tráfico al puerto 80 (Frontend)
az webapp config appsettings set --resource-group $RESOURCE_GROUP --name $WEB_APP_NAME --settings WEBSITES_PORT=80

# Configurar comunicación interna: En Azure Multi-container los contenedores se comunican por localhost
az webapp config appsettings set --resource-group $RESOURCE_GROUP --name $WEB_APP_NAME --settings BACKEND_URL="http://localhost:8080"

# Iniciar la Web App (asegura el arranque si la aplicación está detenida)
az webapp start --name $WEB_APP_NAME --resource-group $RESOURCE_GROUP
```

![Configuración del Contenedor Multi-Contenedor](images/18_configuracion_contenedor_multicontenedor.png)
![Configuración de Variables de Entorno Multi-Contenedor](images/19_configuracion_variables_multicontenedor.png)

**D. Prueba del Despliegue en Azure**
Una vez que App Service haya descargado las imágenes y levantado los contenedores (esto puede tomar 2-3 minutos la primera vez), puedes probar que el flujo multi-contenedor funciona haciendo una llamada a tu dominio `.azurewebsites.net`:

```powershell
# Realizar petición de prueba a la API Frontend desplegada
Invoke-WebRequest "https://$WEB_APP_NAME.azurewebsites.net/generate?prompt=Test_Compose_Azure" -UseBasicParsing
```

![Verificación de la API Multi-Contenedor en Azure](images/20_verificacion_api_azure_compose.png)

*(Nota: Si obtienes un error inicial o un tiempo de espera agotado, espera un par de minutos a que los contenedores terminen de arrancar o ejecuta `az webapp restart --name $WEB_APP_NAME --resource-group $RESOURCE_GROUP` para forzar un reinicio).*

*(Nota para actualizaciones: Si realizas modificaciones en el archivo `docker-compose.yml` localmente y deseas subirlas a Azure, debes volver a cargar la configuración en la Web App ejecutando: `az webapp config container set --resource-group $RESOURCE_GROUP --name $WEB_APP_NAME --multicontainer-config-type compose --multicontainer-config-file docker-compose.yml`).*

## Bloque 3: Despliegue Compose con Persistencia

![Diagrama de Secuencia - Multi-Contenedor v2](images/21_diagrama_arquitectura_v2.png)

Para asegurar que las consultas realizadas a la aplicación no se pierdan cuando se reinician los contenedores o se vuelve a desplegar el servicio en la nube, se ha implementado un mecanismo de almacenamiento persistente montando un recurso compartido de archivos de Azure (Azure File Share) directamente en los contenedores.

El servicio Backend guarda cada prompt en formato de texto plano dentro de la ruta `/app/data/history.txt`. Esta ruta está mapeada a un almacenamiento externo y permanente.

### 3.1. Aprovisionamiento de Azure Files y Conexión con la Web App

Sigue estos pasos en la terminal PowerShell para crear el almacenamiento persistente y conectarlo a tu Web App:

##### Paso 1: Definir variables de entorno adicionales
```powershell
# Variables del entorno de Azure (redefinir si es una sesión de terminal nueva)
$RESOURCE_GROUP  = "gruporecursosia"
$LOCATION        = "spaincentral"
$WEB_APP_NAME    = "webapp-fastapi-gemini"

# Variables para el almacenamiento persistente
$STORAGE_ACCOUNT = "almacenamientoappia" # Debe ser un nombre único globalmente
$SHARE_NAME      = "archivos-texto"
$MOUNT_PATH      = "/app/data" # Ruta dentro del contenedor donde se guardará el historial
```

![Definición de variables de entorno adicionales](images/22_variables.png)

##### Paso 2: Crear la Infraestructura de Almacenamiento
```powershell
# 1. Crear la Cuenta de Almacenamiento (Storage Account)
az storage account create --name $STORAGE_ACCOUNT --resource-group $RESOURCE_GROUP --location $LOCATION --sku Standard_LRS

# 2. Crear el recurso compartido de archivos (File Share)
az storage share-rm create --resource-group $RESOURCE_GROUP --storage-account $STORAGE_ACCOUNT --name $SHARE_NAME --quota 5
```

![Infraestructura de Almacenamiento](images/22_creacion_storage_account_fileshare.png)

##### Paso 3: Conectar el Almacenamiento a la Web App
```powershell
# 1. Obtener la clave de acceso del Storage Account
$STORAGE_KEY = (az storage account keys list --resource-group $RESOURCE_GROUP --account-name $STORAGE_ACCOUNT --query "[0].value" --output tsv)
```

![Obtención de la clave de almacenamiento](images/23_variable.png)

```powershell
# 2. (Opcional) Eliminar un montaje previo con el mismo ID si existe
az webapp config storage-account delete --resource-group $RESOURCE_GROUP --name $WEB_APP_NAME --custom-id AlmacenamientoPersistente

# 3. (Opcional) Limpiar el historial previo en la nube para empezar con una demo limpia (si no existe el archivo, dará error, el cual se puede ignorar)
az storage file delete --share-name $SHARE_NAME --account-name $STORAGE_ACCOUNT --account-key $STORAGE_KEY --path history.txt

# 4. Montar el almacenamiento persistente en la Web App
az webapp config storage-account add --resource-group $RESOURCE_GROUP --name $WEB_APP_NAME --custom-id AlmacenamientoPersistente --storage-type AzureFiles --account-name $STORAGE_ACCOUNT --share-name $SHARE_NAME --access-key $STORAGE_KEY --mount-path $MOUNT_PATH

# 4. Reiniciar la Web App para que el montaje surta efecto
az webapp restart --name $WEB_APP_NAME --resource-group $RESOURCE_GROUP
```

![Conexión de Almacenamiento](images/23_montaje_storage_webapp.png)

---

### 3.2. Ajuste al Docker Compose (`docker-compose.yml`)

Para soportar las pruebas y persistencia en local, se actualiza el `docker-compose.yml` añadiendo el volumen persistente al servicio `backend` y etiquetando las imágenes como `v2`. El archivo completo queda así:

```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    image: planservicioia.azurecr.io/fastapi-backend:v2
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
    expose:
      - "8080"
    volumes:
      - AlmacenamientoPersistente:/app/data

  frontend:
    build: ./frontend
    image: planservicioia.azurecr.io/fastapi-frontend:v2
    environment:
      - BACKEND_URL=http://backend:8080
    ports:
      - "80:80"
    depends_on:
      - backend

volumes:
  AlmacenamientoPersistente:
```
* **En Local:** docker-compose crea y gestiona automáticamente un volumen local llamado `AlmacenamientoPersistente` que se monta en `/app/data` y persiste los datos de tus consultas.
* **En Azure:** Azure App Service intercepta el nombre del volumen (`AlmacenamientoPersistente`) y lo asocia automáticamente con el montaje de Azure Files que tiene el mismo `custom-id` (Paso 3), guardando el archivo de texto directamente en la cuenta de almacenamiento en la nube sin depender del almacenamiento efímero del contenedor.

---

### 3.3. Pruebas de Persistencia en Local

> **⚠️ Prerequisito:** Comprueba que **Docker Desktop** está en ejecución antes de continuar (icono en la barra de tareas → *"Docker Desktop is running"*).

1. Levanta los contenedores en local:
   ```powershell
   docker-compose up --build -d
   ```
2. Envía prompts de prueba al endpoint público de generación (puerto 80):
   ```powershell
   Invoke-WebRequest "http://localhost:80/generate?prompt=Local_Prompt_1" -UseBasicParsing
   Invoke-WebRequest "http://localhost:80/generate?prompt=Local_Prompt_2" -UseBasicParsing
   ```
3. Verifica que se ha creado el historial accediendo al endpoint `/history`:
   ```powershell
   (Invoke-WebRequest "http://localhost:80/history" -UseBasicParsing).Content
   # Salida esperada: {"history":["Local_Prompt_1"]}
   ```

![Prueba de Historial en Local](images/24_prueba_historial_local.png)

4. Detén y elimina por completo los contenedores:
   ```powershell
   docker-compose down
   ```
5. Vuelve a levantar el servicio:
   ```powershell
   docker-compose up -d
   ```
6. Consulta nuevamente el historial.
   ```powershell
   (Invoke-WebRequest "http://localhost:80/history" -UseBasicParsing).Content
   # Salida esperada: {"history":["Local_Prompt_1"]}
   ```
Los datos deben seguir presentes puesto que están guardados en el archivo `./data/history.txt` de tu equipo local y sobreviven a la recreación de los contenedores.

![Prueba de Persistencia en Local](images/24_prueba_persistencia_local.png)

---

### 3.4. Pruebas de Persistencia en Azure

1. Reconstruye y sube las imágenes al ACR con los nuevos cambios de código:
   ```powershell
   $env:ACR_NAME=$ACR_NAME
   docker-compose build
   docker-compose push
   ```

   ![Compilación y subida de imágenes](images/25_build.png)

   > **ℹ️ Nota:** La advertencia (*warning*) relacionada con la versión de Docker Compose en la construcción de imágenes se corregirá más adelante.

2. Actualiza la configuración de la Web App con el nuevo `docker-compose.yml` (que incluye el volumen) y fuerza el reinicio:
   ```powershell
   # Subir la nueva configuración del compose a Azure (incluye el volumen en backend)
   az webapp config container set --resource-group $RESOURCE_GROUP --name $WEB_APP_NAME --multicontainer-config-type compose --multicontainer-config-file docker-compose.yml

   # Reiniciar para descargar las nuevas imágenes y aplicar el montaje
   az webapp restart --name $WEB_APP_NAME --resource-group $RESOURCE_GROUP
   ```

   ![Configuración del contenedor en Azure](images/25_config.png)

3. Envía una consulta a la Web App en la nube:
   ```powershell
   Invoke-WebRequest "https://webapp-fastapi-gemini.azurewebsites.net/generate?prompt=Azure_Prompt_1" -UseBasicParsing
   ```
4. Consulta el endpoint de historial para comprobar que ha registrado la consulta:
   ```powershell
   (Invoke-WebRequest "https://webapp-fastapi-gemini.azurewebsites.net/history" -UseBasicParsing).Content
   # Salida esperada: {"history":["Azure_Prompt_1"]}
   ```

   ![Consulta de historial en Azure](images/25_history.png)

5. (Opcional) Verifica la persistencia listando los archivos en Azure File Share directamente mediante Azure CLI:
   ```powershell
   # Listar archivos en el File Share
   az storage file list --share-name $SHARE_NAME --account-name $STORAGE_ACCOUNT --account-key $STORAGE_KEY --output table

   # Descargar y mostrar el contenido de history.txt
   az storage file download --share-name $SHARE_NAME --account-name $STORAGE_ACCOUNT --account-key $STORAGE_KEY --path history.txt --dest .
   Get-Content history.txt
   Remove-Item history.txt
   ```

   ![Verificación opcional de persistencia en Azure Files](images/25_opcional.png)

6. Forza un reinicio de la Web App en Azure para simular un fallo o actualización del servicio:
   ```powershell
   az webapp restart --name $WEB_APP_NAME --resource-group $RESOURCE_GROUP
   ```
7. Vuelve a realizar la consulta al historial tras esperar un par de minutos:
   ```powershell
   (Invoke-WebRequest "https://webapp-fastapi-gemini.azurewebsites.net/history" -UseBasicParsing).Content
   ```
   **Resultado:** El endpoint debe seguir devolviendo `{"history":["Azure_Prompt_1"]}` demostrando que el archivo se almacena en el volumen persistente de Azure Files y no se pierde tras reiniciar el servicio.

   ![Prueba de Persistencia en Azure](images/25_prueba_persistencia_azure.png)

   *(Nota: Es posible que aparezcan más entradas en la lista del historial si ya habías lanzado peticiones de prueba anteriormente).*

---

## Bloque 4: Despliegue Final con Persistencia y Prueba de Interconexión

### 4.1. Diagrama de Arquitectura Final

![Diagrama de Arquitectura Final](images/26_diagrama_arquitectura_v3.png)

En esta nueva iteración de la arquitectura (imágenes etiquetadas con la versión `v3`), se ha modificado la demostración de la comunicación de red entre contenedores de la siguiente forma:

1. **Reemplazo de `/history`:** Se eliminó la anterior funcionalidad de historial de prompts que gestionaba el Backend en `history.txt`.
2. **Generación de Logs en Frontend:** Ahora, el Frontend (Contenedor A) usa la librería estándar `logging` de Python para registrar cada comunicación con el Backend (Contenedor B) en el archivo `history.txt`.
3. **Endpoint `/logs`:** Se habilitó un nuevo endpoint en el Frontend (`GET /logs`) para leer de forma local el archivo de logs `history.txt` y retornar los registros del flujo de peticiones.
4. **Reubicación de Volumen:** El volumen persistente `AlmacenamientoPersistente` ha sido reubicado en el Frontend para conservar el historial de logs ante reinicios.

### 4.2. Configuración en docker-compose (Versión v3)

El archivo `docker-compose.yml` actualiza las imágenes a la versión `v3` y traslada el volumen persistente al servicio `frontend`:

```yaml
services:
  backend:
    build: ./backend
    image: planservicioia.azurecr.io/fastapi-backend:v3
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
    expose:
      - "8080"

  frontend:
    build: ./frontend
    image: planservicioia.azurecr.io/fastapi-frontend:v3
    environment:
      - BACKEND_URL=http://backend:8080
    ports:
      - "80:80"
    depends_on:
      - backend
    volumes:
      - AlmacenamientoPersistente:/app/data

volumes:
  AlmacenamientoPersistente:
```

### 4.3. Definición de los Contenedores (Dockerfiles)

Para la construcción de los contenedores de Frontend y Backend de esta arquitectura final, se utilizan los siguientes archivos `Dockerfile`:

#### Backend (`backend/Dockerfile`)
```dockerfile
# Use official Python slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements.txt first to leverage Docker cache
COPY requirements.txt .

# Install all dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the FastAPI app
COPY app.py .

# Expose FastAPI port
EXPOSE 8080

# Run the app with Uvicorn
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
```

#### Frontend (`frontend/Dockerfile`)
```dockerfile
# Use official Python slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements.txt first to leverage Docker cache
COPY requirements.txt .

# Install all dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the FastAPI app
COPY app.py .

# Expose FastAPI port
EXPOSE 80

# Run the app with Uvicorn on port 80
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "80"]
```

### 4.4. Pruebas de Logs y Persistencia en Local

> **⚠️ Prerequisito:** Comprueba que **Docker Desktop** está en ejecución antes de continuar (icono en la barra de tareas → *"Docker Desktop is running"*).

1. Lee la API Key de Gemini desde el archivo `.env` local:
   ```powershell
   # Leer la API Key desde el archivo .env
   $env:GEMINI_API_KEY = (Get-Content .env | Select-String "GEMINI_API_KEY" | ForEach-Object { $_.ToString().Split("=",2)[1] })
   ```

   ![Carga de variables locales](images/27_env_local.png)

   Posteriormente, construye y levanta los contenedores con las imágenes `v3`:
   ```powershell
   docker-compose up --build -d
   ```
2. Envía una consulta de prueba al frontend (puerto 80):
   ```powershell
   Invoke-WebRequest "http://localhost:80/generate?prompt=Test_Communication_Logs"
   ```
3. Verifica la traza de logs de comunicación a través del endpoint `/logs`:
   ```powershell
   (Invoke-WebRequest "http://localhost:80/logs").Content
   ```
   **Salida esperada (en formato JSON):**
   ```json
   {
     "logs": [
       "2026-06-04 20:50:44,123 - INFO - Enviando prompt al servicio B en la URL http://backend:8080/generate",
       "2026-06-04 20:50:44,456 - INFO - Respuesta exitosa recibida del servicio B."
     ]
   }
   ```

   ![Prueba de comunicación y logs en local](images/27_prueba_comunicacion_logs_local.png)

4. Detén y elimina por completo los contenedores para validar la persistencia:
   ```powershell
   docker-compose down
   ```
5. Vuelve a iniciar los contenedores (esta vez sin reconstruir la imagen):
   ```powershell
   docker-compose up -d
   ```
6. Consulta nuevamente el endpoint de logs:
   ```powershell
   (Invoke-WebRequest "http://localhost:80/logs" -UseBasicParsing).Content
   ```
   **Resultado:** El endpoint debe seguir devolviendo los registros de logs previos (`"INFO - Enviando prompt..."` y `"INFO - Respuesta exitosa..."`), demostrando que el archivo se almacena en el volumen persistente `AlmacenamientoPersistente` en tu equipo local y sobrevive a la recreación de los contenedores.

   ![Persistencia de logs tras recreación de contenedores](images/28_persistencia_logs_tras_reinicio_local.png)

### 4.5. Guía de Pasos Realizados (Despliegue Completo en Azure desde Cero)

Aunque la creación de los recursos de Azure y la configuración de red y almacenamiento se realizaron de forma iterativa en las secciones previas de este documento (Bloques 1 al 3), a continuación se presenta la secuencia completa de comandos PowerShell en un formato completamente autocontenido para permitir realizar el despliegue del servicio final desde un entorno completamente limpio de extremo a extremo:

#### Paso 1: Autenticación en Azure y definición de variables de entorno
Inicia sesión en Azure mediante CLI:

```powershell
# Autenticarse en Azure y seleccionar plan de estudiantes pulsando Enter
az login
```

![Autenticación en Azure](images/03_login.png)

Define todas las variables de entorno necesarias para la creación de los recursos:

```powershell
# Definir variables de entorno de Azure
$RESOURCE_GROUP   = "gruporecursosia"
$LOCATION         = "spaincentral"
$ACR_NAME         = "planservicioia"
$APP_SERVICE_PLAN = "plan-fastapi-gemini"
$WEB_APP_NAME     = "webapp-fastapi-gemini"
$STORAGE_ACCOUNT  = "almacenamientoappia" # Debe ser un nombre único globalmente
$SHARE_NAME       = "archivos-texto"
$MOUNT_PATH       = "/app/data"

# Obtener la contraseña de administrador
$ACR_PASSWORD = (az acr credential show --name $ACR_NAME --query "passwords[0].value" -o tsv)

# Leer la API Key de Gemini desde el archivo .env (evita exponer la clave en el historial de comandos)
$GEMINI_API_KEY = (Get-Content .env | Select-String "GEMINI_API_KEY" | ForEach-Object { $_.ToString().Split("=",2)[1] })
```

![Variables de entorno cargadas](images/27_vars.png)

#### Paso 2: Creación del Grupo de Recursos y del Azure Container Registry (ACR)
Crea el contenedor lógico para agrupar los servicios y aprovisiona el registro privado de Docker:

```powershell
# Crear el grupo de recursos
az group create --name $RESOURCE_GROUP --location $LOCATION

# Crear el Azure Container Registry (SKU básico)
az acr create --name $ACR_NAME --resource-group $RESOURCE_GROUP --sku Basic
```

![Creación del Grupo de Recursos y del Azure Container Registry](images/27_grupo.png)

#### Paso 3: Creación de la Cuenta de Almacenamiento y del File Share (Azure Files)
Aprovisiona la cuenta de almacenamiento:

```powershell
# 1. Crear la Cuenta de Almacenamiento (Storage Account)
az storage account create --name $STORAGE_ACCOUNT --resource-group $RESOURCE_GROUP --location $LOCATION --sku Standard_LRS
```

![Creación de la Cuenta de Almacenamiento](images/27_storageacc.png)

Crea el recurso compartido de archivos donde se alojará el historial de logs de comunicación de forma persistente:

```powershell
# 2. Crear el recurso compartido de archivos (File Share)
az storage share-rm create --resource-group $RESOURCE_GROUP --storage-account $STORAGE_ACCOUNT --name $SHARE_NAME --quota 5
```

![Creación del recurso compartido de archivos](images/27_share.png)

#### Paso 4: Habilitar usuario administrador en ACR y autenticarse localmente
Habilita el acceso administrador del registro privado para obtener las credenciales de publicación:

```powershell
# Habilitar usuario admin del registro
az acr update -n $ACR_NAME --admin-enabled true
```

![Habilitación de usuario administrador en ACR](images/27_admin.png)

Inicia sesión en Docker local:

```powershell
# Iniciar sesión local en Docker con las credenciales de ACR (usando password-stdin por seguridad)
echo $ACR_PASSWORD | docker login "$ACR_NAME.azurecr.io" --username $ACR_NAME --password-stdin
```

![Autenticación local en Docker](images/27_echo.png)

> **ℹ️ Nota:** Al realizar la autenticación local con Docker, es posible que la aplicación de **Docker Desktop** se ponga temporalmente en primer plano (*foreground*) para gestionar el almacenamiento seguro de las credenciales de ACR.

#### Paso 5: Construcción y subida de las imágenes Docker v3
Utiliza docker-compose para compilar las imágenes del Frontend y del Backend etiquetadas con la versión `v3`, y súbelas al ACR:

```powershell
# Exportamos el nombre del ACR para los tags del Compose
$env:ACR_NAME=$ACR_NAME

# Construimos y subimos las imágenes
docker-compose build
docker-compose push
```

![docker-compose build y push de imágenes v3](images/27_build.png)

#### Paso 6: Creación del Plan de App Service y de la Web App Multi-Container
Aprovisiona el plan de hospedaje de computación Linux:

```powershell
# Crear el Plan de App Service (SKU B1 de Linux)
az appservice plan create --name $APP_SERVICE_PLAN --resource-group $RESOURCE_GROUP --sku B1 --is-linux
```

![Creación del Plan de App Service](images/27_appservice.png)

Crea la Web App asociándola directamente con la definición del archivo `docker-compose.yml`:

```powershell
# Crear la Web App pasándole el docker-compose.yml directamente
az webapp create --resource-group $RESOURCE_GROUP --plan $APP_SERVICE_PLAN --name $WEB_APP_NAME --multicontainer-config-type compose --multicontainer-config-file docker-compose.yml
```

![Creación de la Web App en Azure](images/27_webapp.png)

#### Paso 7: Configuración de Credenciales de Registro y Variables de Entorno
Vincula la autenticación del registro privado a la Web App para que pueda descargar las imágenes e inyecta los secretos y variables de entorno necesarios:

```powershell
# Vincular las credenciales del ACR a la Web App
az webapp config container set --name $WEB_APP_NAME --resource-group $RESOURCE_GROUP --container-registry-url "https://$ACR_NAME.azurecr.io" --container-registry-user $ACR_NAME --container-registry-password $ACR_PASSWORD

# Configurar variables de entorno: API Key de Gemini, puerto público (80) y URL del backend (localhost:8080)
az webapp config appsettings set --resource-group $RESOURCE_GROUP --name $WEB_APP_NAME --settings GEMINI_API_KEY=$GEMINI_API_KEY WEBSITES_PORT=80 BACKEND_URL="http://localhost:8080"
```

![Configuración de la Web App en Azure](images/27_webapp_config.png)

> **ℹ️ Nota:** En Azure App Service Multi-container los contenedores comparten el mismo espacio de red (host local), por lo que el Frontend debe llamar al Backend mediante `http://localhost:8080` en lugar de `http://backend:8080`.

#### Paso 8: Montaje del Almacenamiento Persistente en la Web App
Obtén las credenciales de acceso del Storage Account y monta el File Share en la ruta `/app/data` para que el contenedor de Frontend pueda registrar los logs de forma persistente:

```powershell
# 1. Obtener la clave de acceso del Storage Account
$STORAGE_KEY = (az storage account keys list --resource-group $RESOURCE_GROUP --account-name $STORAGE_ACCOUNT --query "[0].value" --output tsv)

# 2. (Opcional) Eliminar un montaje previo y el archivo history.txt si existe. Para ello, detiene la webapp, elimina el montaje y el archivo history.txt. En este caso ya no existe
az webapp stop --name $WEB_APP_NAME --resource-group $RESOURCE_GROUP
az webapp config storage-account delete --resource-group $RESOURCE_GROUP --name $WEB_APP_NAME --custom-id AlmacenamientoPersistente
az storage file delete --share-name $SHARE_NAME --account-name $STORAGE_ACCOUNT --account-key $STORAGE_KEY --path history.txt

# 4. Montar el almacenamiento persistente en la Web App
az webapp config storage-account add --resource-group $RESOURCE_GROUP --name $WEB_APP_NAME --custom-id AlmacenamientoPersistente --storage-type AzureFiles --account-name $STORAGE_ACCOUNT --share-name $SHARE_NAME --access-key $STORAGE_KEY --mount-path /app/data
```

![Configuración del almacenamiento persistente en Azure](images/30_configuracion_storage_azure_v3.png)

#### Paso 9: Arranque y Verificación de la Arquitectura Final
Arranca la Web App, espera unos minutos a que los contenedores estén completamente listos y valida la interconexión entre ambos así como la persistencia de logs:

```powershell
# Iniciar la Web App
az webapp start --name $WEB_APP_NAME --resource-group $RESOURCE_GROUP
```

> ⏳ **Esperar ~2 minutos** a que los contenedores completen su arranque e inicialización en Azure antes de realizar la verificación.

> **ℹ️ Nota para usuarios de Linux:** Si realizas la verificación desde una línea de comandos de Linux, puedes sustituir `Invoke-WebRequest` (y su posterior `.Content` en PowerShell) por `curl -s`. Por ejemplo:
> ```bash
> curl -s "https://webapp-fastapi-gemini.azurewebsites.net/generate?prompt=Azure_Prompt_v3"
> ```

1. **Prueba de generación de contenido (Frontend llama al Backend internamente):**
   ```powershell
   Invoke-WebRequest "https://webapp-fastapi-gemini.azurewebsites.net/generate?prompt=Azure_Prompt_v3" -UseBasicParsing
   ```
   *(Nota: Si la primera petición devuelve un error de "ConnectError('All connection attempts failed')", espera un momento y vuelve a intentarlo mientras el contenedor backend finaliza su arranque).*

2. **Consulta del endpoint de logs para verificar la traza de comunicaciones internas:**
   ```powershell
   (Invoke-WebRequest "https://webapp-fastapi-gemini.azurewebsites.net/logs" -UseBasicParsing).Content
   ```
   **Salida esperada:**
   ```json
   {
     "logs": [
       "2026-06-21 21:54:12,345 - INFO - Enviando prompt al servicio B en la URL http://localhost:8080/generate",
       "2026-06-21 21:54:13,123 - INFO - Respuesta exitosa recibida del servicio B."
     ]
   }
   ```

   ![Logs de interconexión y peticiones en Azure](images/30_req_azure.png)

3. **(Opcional) Comprobar existencia física del log en Azure Files:**
   ```powershell
   # Listar archivos en el File Share
   az storage file list --share-name $SHARE_NAME --account-name $STORAGE_ACCOUNT --account-key $STORAGE_KEY --output table

   # Descargar y mostrar el contenido
   az storage file download --share-name $SHARE_NAME --account-name $STORAGE_ACCOUNT --account-key $STORAGE_KEY --path history.txt --dest .
   Get-Content history.txt
   Remove-Item history.txt
   ```

   ![Existencia física de logs en Azure Files](images/30_check_storage.png)

4. **Prueba de persistencia de logs tras reinicio:**
   Forza la recreación del servicio simulando un fallo o actualización y comprueba que el historial no se ha perdido:
   ```powershell
   # Reiniciar la Web App
   az webapp restart --name $WEB_APP_NAME --resource-group $RESOURCE_GROUP
   ```
   ⏳ Espera de nuevo el arranque y consulta los logs:
   ```powershell
   (Invoke-WebRequest "https://webapp-fastapi-gemini.azurewebsites.net/logs" -UseBasicParsing).Content
   ```

   ![Prueba de persistencia de logs en Azure](images/31_prueba_persistencia_logs_azure.png)

---

## Referencias y Bibliografía

Para la elaboración de este despliegue y la configuración de los comandos utilizados a lo largo de la práctica, se han consultado las siguientes fuentes de documentación oficial:

### Documentación de Azure CLI (Microsoft Learn):
* [az login (Autenticación en Azure)](https://learn.microsoft.com/cli/azure/reference-index#az-login)
* [az group (Administración de Grupos de Recursos)](https://learn.microsoft.com/cli/azure/group)
* [az acr (Gestión de Azure Container Registry)](https://learn.microsoft.com/cli/azure/acr)
* [az acr credential (Obtención de Credenciales del Registro)](https://learn.microsoft.com/cli/azure/acr/credential)
* [az appservice plan (Configuración de Planes de App Service)](https://learn.microsoft.com/cli/azure/appservice/plan)
* [az webapp (Creación y Gestión de Web Apps)](https://learn.microsoft.com/cli/azure/webapp)
* [az webapp config container (Configuración de Contenedores en Web Apps)](https://learn.microsoft.com/cli/azure/webapp/config/container)
* [az webapp config appsettings (Definición de Variables de Entorno y Configuración)](https://learn.microsoft.com/cli/azure/webapp/config/appsettings)
* [az webapp config storage-account (Montaje de Almacenamiento en Web Apps)](https://learn.microsoft.com/cli/azure/webapp/config/storage-account)
* [az webapp log (Descarga y Seguimiento de Logs en Tiempo Real)](https://learn.microsoft.com/cli/azure/webapp/log)
* [az storage account (Gestión de Cuentas de Almacenamiento)](https://learn.microsoft.com/cli/azure/storage/account)
* [az storage share-rm (Gestión de Recursos Compartidos de Azure Files)](https://learn.microsoft.com/cli/azure/storage/share-rm)

### Documentación de Docker:
* [Referencia de la Línea de Comandos de Docker (build, push, run, login)](https://docs.docker.com/engine/reference/commandline/cli/)
* [Guía de Referencia del Archivo Dockerfile](https://docs.docker.com/engine/reference/builder/)
* [Docker Compose — Referencia de la CLI (up, down, build, push)](https://docs.docker.com/compose/reference/)
* [Docker Compose — Especificación del Archivo docker-compose.yml](https://docs.docker.com/compose/compose-file/)

### PowerShell:
* [Invoke-WebRequest (Cmdlet para peticiones HTTP)](https://learn.microsoft.com/powershell/module/microsoft.powershell.utility/invoke-webrequest)

### Librerías y SDKs:
* [Documentación Oficial de FastAPI (Framework Web)](https://fastapi.tiangolo.com/)
* [SDK de Google GenAI para Python (Gemini 2.5)](https://github.com/googleapis/python-genai)
* [httpx — Cliente HTTP asíncrono para Python](https://www.python-httpx.org/)

---

## Anexo: Enlaces del Proyecto

A continuación se facilitan los enlaces correspondientes al repositorio de código fuente y a la demostración del despliegue:

* **Repositorio de GitHub:** [danielquinti/azure-assignment](https://github.com/danielquinti/azure-assignment)
* **Código de la primera versión (Bloque 1):** [Release v1 de GitHub](https://github.com/danielquinti/azure-assignment/releases/tag/v1)
* **Código de la segunda versión (Bloque 2):** [Release v1-compose de GitHub](https://github.com/danielquinti/azure-assignment/releases/tag/v1-compose)
* **Código de la tercera versión (Bloque 3):** [Release v2 de GitHub](https://github.com/danielquinti/azure-assignment/releases/tag/v2)
* **Prueba de Despliegue (Vídeo):** [Demostración en vídeo de la práctica (SharePoint)](https://udcgal-my.sharepoint.com/:v:/g/personal/daniel_quintillan_udc_es/IQAZx4uVDzvRSLAc_VQAiSLoAaY_CBG_JocwCdQYRb9-5mE?e=e3HjUF)
