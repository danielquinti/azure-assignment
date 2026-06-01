# Práctica PaaS: Despliegue de Servicio GenAI en Azure App Service (Rama Mínimo)

Este documento detalla la estructura, generación de imagen y flujo de comandos para realizar el despliegue del servicio mínimo en **Azure App Service (PaaS)** sobre Linux. El servicio consiste en un único contenedor que expone una API desarrollada en **FastAPI** que conecta con la API de **Gemini** para procesar prompts de usuario.

---

## 1. Descripción del Despliegue (Arquitectura Mínima)

El despliegue consiste en un servicio web serverless autohospedado dentro de un contenedor Docker en la plataforma **Azure App Service (Linux Web App)**. 

### Características del despliegue:
* **Sin Persistencia:** El contenedor funciona bajo el principio de infraestructura efímera (stateless). Las solicitudes se procesan en tiempo real y no se guarda historial de las consultas en archivos locales ni bases de datos.
* **Único Contenedor:** Toda la lógica reside en una sola aplicación de FastAPI, eliminando la necesidad de proxies o bases de datos adicionales.
* **Integración GenAI:** Se conecta directamente con la API oficial de Google Gemini usando el SDK de nueva generación (`google-genai`) y la clave de API `GEMINI_API_KEY` inyectada mediante variables de entorno en la nube.
* **Infraestructura PaaS:** Se emplea un plan de App Service en Linux, ideal para albergar APIs basadas en contenedores con escalado automático de recursos.

```
                  ┌───────────────────────────────┐
                  │      Azure App Service        │
                  │   (Linux Web App Container)   │
                  │                               │
Cliente (HTTP) ──>│  ┌─────────────────────────┐  │      HTTPS
  [Port 80/443]   │  │       FastAPI App       │──┼───────────────> Google Gemini API
                  │  │       [Port 8080]       │  │ (gemini-2.5-flash)
                  │  └─────────────────────────┘  │
                  └───────────────────────────────┘
```

---

## 2. Definición del Contenedor (Dockerfile)

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

### Código de la Aplicación (`app.py`):
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

## 3. Pruebas y Validación en Local

Antes de proceder con el despliegue en la nube, se recomienda validar el correcto funcionamiento de la aplicación de manera local mediante Docker.

### Ejecución mediante Docker local
Construya la imagen localmente y levante el contenedor pasando la variable de entorno:

```powershell
# Construir la imagen local
docker build -t fastapi-gemini:local .

# Ejecutar el contenedor
docker run -d -p 8080:8080 --name fastapi-app-local -e GEMINI_API_KEY="TU_API_KEY_DE_GEMINI" fastapi-gemini:local
```

### Verificación local:
Realice una llamada de prueba desde el navegador o consola al puerto local `8080`:

```powershell
Invoke-WebRequest "http://localhost:8080/generate?prompt=Hello_Local_Testing"
```

![Prueba local exitosa](local.png)

---

## 4. Guía de Pasos Realizados (Despliegue en Azure)

A continuación se presenta la secuencia completa de comandos ejecutados en la consola para registrar la imagen de contenedor y aprovisionar la infraestructura en Azure.

### Paso 1: Autenticación en Azure y definición de variables
Inicie sesión en su suscripción de Azure mediante CLI y defina las variables del entorno de trabajo:

```powershell
# Autenticarse en Azure
az login

# Definir variables de entorno para los comandos
$RESOURCE_GROUP = "gruporecursosia"
$LOCATION = "spaincentral"
$ACR_NAME = "planservicioia"
$APP_SERVICE_PLAN = "plan-fastapi-gemini"
$WEB_APP_NAME = "webapp-fastapi-gemini"
$IMAGE_TAG = "planservicioia.azurecr.io/fastapi-gemini:v1"
```

### Paso 2: Creación del Grupo de Recursos y del Azure Container Registry (ACR)
Cree un grupo de recursos donde se alojarán todos los componentes y aprovisione el registro de contenedores privado:

```powershell
# Crear el grupo de recursos
az group create --name $RESOURCE_GROUP --location $LOCATION
```

![Grupo de Recursos](gruporecursos.png)

```powershell
# Crear el Azure Container Registry (SKU básico para desarrollo/pruebas)
az acr create --name $ACR_NAME --resource-group $RESOURCE_GROUP --sku Basic
```

![Azure Container Registry](acr.png)

### Paso 3: Habilitar usuario administrador en ACR y autenticarse localmente
Habilite el acceso de administrador para obtener las credenciales de lectura/escritura de imágenes directamente desde Docker:

```powershell
# Habilitar usuario admin del registro
az acr update -n $ACR_NAME --admin-enabled true
```

![Habilitar Administrador ACR](admin.png)

```powershell
# Obtener la contraseña de administrador
$ACR_PASSWORD = (az acr credential show --name $ACR_NAME --query "passwords[0].value" -o tsv)

# Iniciar sesión local en Docker con las credenciales de ACR
docker login "$ACR_NAME.azurecr.io" --username $ACR_NAME --password $ACR_PASSWORD
```

![Autenticación Docker local](dockercred.png)

### Paso 4: Construcción y subida de la imagen Docker
Construya la imagen Docker localmente etiquetándola con la URI del registro de Azure, y súbala al repositorio:

```powershell
# Construir la imagen usando el Dockerfile de la raíz
docker build -t $IMAGE_TAG .
```

![Construcción de la imagen Docker](docker build.png)

```powershell
# Subir la imagen a Azure Container Registry
docker push $IMAGE_TAG
```

![Subida de la imagen a ACR](push.png)

### Paso 5: Creación del Plan de App Service
Aprovisione un plan de hospedaje en Azure App Service configurado en Linux:

```powershell
# Crear el Plan de App Service (SKU B1 de Linux como nivel básico de desarrollo)
az appservice plan create --name $APP_SERVICE_PLAN --resource-group $RESOURCE_GROUP --sku B1 --is-linux
```

![Creación del Plan de App Service](plan.png)

### Paso 6: Despliegue de la Web App desde el ACR
Aprovisione la Web App de contenedores configurando la imagen previamente cargada en el registro de Azure:

```powershell
# Crear la Web App con la imagen del contenedor de Azure
az webapp create --resource-group $RESOURCE_GROUP --plan $APP_SERVICE_PLAN --name $WEB_APP_NAME --deployment-container-image-name $IMAGE_TAG
```

![Creación de la Web App en Azure](create_webapp.png)

### Paso 7: Configuración de Credenciales de Registro y Variables de Entorno
Configure la autenticación del App Service contra el ACR para que pueda descargar las actualizaciones de la imagen y defina los secretos de la aplicación:

```powershell
# Vincular las credenciales del registro privado a la Web App
az webapp config container set --name $WEB_APP_NAME --resource-group $RESOURCE_GROUP --docker-custom-image-name $IMAGE_TAG --docker-registry-server-url "https://$ACR_NAME.azurecr.io" --docker-registry-server-user $ACR_NAME --docker-registry-server-password $ACR_PASSWORD

# Definir la API Key de Gemini y forzar el puerto 8080 dentro del contenedor
az webapp config appsettings set --resource-group $RESOURCE_GROUP --name $WEB_APP_NAME --settings WEBSITES_PORT=8080 GEMINI_API_KEY="TU_API_KEY_DE_GEMINI"
```

![Configuración de la Web App en Azure](webappconfig.png)

---

## 5. Verificación del Funcionamiento en Azure

Una vez que el despliegue haya completado su inicio en Azure, puede probar el endpoint de generación ejecutando la siguiente llamada HTTP desde la consola:

```powershell
# Realizar petición de prueba a la API desplegada en Azure
Invoke-WebRequest "https://$WEB_APP_NAME.azurewebsites.net/generate?prompt=Explain_PaaS_in_one_sentence"
```

### Formato esperado de respuesta:
```json
{
  "prompt": "Explain_PaaS_in_one_sentence",
  "text": "Platform as a Service (PaaS) is a cloud computing model where a third-party provider delivers hardware and software tools—usually those needed for application development—to users over the internet."
}
```

![Verificación de la API en Azure](azuretest.png)

### 5.1. Limpieza de Recursos y Control de Gastos

Para evitar que los recursos aprovisionados sigan consumiendo créditos de estudiante o facturando cargos adicionales, se recomienda gestionar el ciclo de vida de los servicios mediante una de las siguientes opciones:

Si deseas conservar la configuración de la Web App pero detener la ejecución del contenedor:
```powershell
# Detener la Web App
az webapp stop --name $WEB_APP_NAME --resource-group $RESOURCE_GROUP

# Volver a iniciar el servicio cuando sea necesario
az webapp start --name $WEB_APP_NAME --resource-group $RESOURCE_GROUP
```
## 6. Referencias y Bibliografía

Para la elaboración de este despliegue y la configuración de los comandos, se han consultado las siguientes fuentes de documentación oficial:

### Documentación de Azure CLI (Microsoft Learn):
* [az group (Administración de Grupos de Recursos)](https://learn.microsoft.com/cli/azure/group)
* [az acr (Gestión de Azure Container Registry)](https://learn.microsoft.com/cli/azure/acr)
* [az appservice plan (Configuración de Planes de App Service)](https://learn.microsoft.com/cli/azure/appservice/plan)
* [az webapp (Creación y Gestión de Web Apps)](https://learn.microsoft.com/cli/azure/webapp)
* [az webapp config container (Configuración de Contenedores en Web Apps)](https://learn.microsoft.com/cli/azure/webapp/config/container)
* [az webapp config appsettings (Definición de Variables de Entorno y Configuración)](https://learn.microsoft.com/cli/azure/webapp/config/appsettings)

### Documentación de Docker:
* [Referencia de la Línea de Comandos de Docker (build, push, run)](https://docs.docker.com/engine/reference/commandline/cli/)
* [Guía de Referencia del Archivo Dockerfile](https://docs.docker.com/engine/reference/builder/)

### Librerías y SDKs:
* [Documentación Oficial de FastAPI (Framework Web)](https://fastapi.tiangolo.com/)
* [SDK de Google GenAI para Python (Gemini 2.5)](https://github.com/googleapis/python-genai)

