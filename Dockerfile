# -------------------------------------------------
# Etapa base: imagen ligera de Python con LibreOffice
# -------------------------------------------------
FROM python:3.11-slim

# Evita prompts interactivos
ENV DEBIAN_FRONTEND=noninteractive

# Instalar dependencias del sistema (LibreOffice + utilidades)
RUN apt-get update && \
    apt-get install -y libreoffice libreoffice-writer fonts-dejavu-core && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Crear directorio de trabajo
WORKDIR /app

# Copiar archivos del proyecto
COPY . /app

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Crear carpetas necesarias
RUN mkdir -p templates outputs

# Exponer puerto de FastAPI
EXPOSE 8000

# Comando de ejecución
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]