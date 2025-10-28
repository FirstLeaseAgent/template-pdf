from fastapi import FastAPI, UploadFile, File, HTTPException, Path, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from docx import Document
from docx2pdf import convert
from datetime import datetime
import json
import os
import uuid
from utils.parser import extraer_variables

app = FastAPI(title="Template PDF Service")

TEMPLATES_DIR = "templates"
OUTPUT_DIR = "outputs"
DB_PATH = "db.json"

os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Inicializar DB si no existe
if not os.path.exists(DB_PATH):
    with open(DB_PATH, "w") as f:
        json.dump({"plantillas": []}, f)

# ============================================================
# Subir Plantilla
# ============================================================
@app.post("/upload_template")
async def upload_template(file: UploadFile = File(...)):
    if not file.filename.endswith(".docx"):
        raise HTTPException(status_code=400, detail="Solo se permiten archivos .docx")

    plantilla_id = str(uuid.uuid4())
    path = os.path.join(TEMPLATES_DIR, file.filename)
    with open(path, "wb") as f:
        f.write(await file.read())

    variables = extraer_variables(path)

    with open(DB_PATH, "r+") as db:
        data = json.load(db)
        data["plantillas"].append({
            "id": plantilla_id,
            "nombre": file.filename,
            "variables": variables
        })
        db.seek(0)
        json.dump(data, db, indent=4)

    return {"id": plantilla_id, "nombre": file.filename, "variables": variables}

# ============================================================
# Generar documento Word + PDF
# ============================================================
@app.post("/generate")
async def generate(request: Request):
    data = await request.json()
    plantilla_id = data.get("plantilla_id")
    valores = data.get("valores", {})

    with open(DB_PATH, "r") as f:
        db = json.load(f)

    plantilla = next((p for p in db["plantillas"] if p["id"] == plantilla_id), None)
    if not plantilla:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")

    plantilla_path = os.path.join(TEMPLATES_DIR, plantilla["nombre"])
    if not os.path.exists(plantilla_path):
        raise HTTPException(status_code=404, detail="Archivo de plantilla no encontrado")

    doc = Document(plantilla_path)

    for p in doc.paragraphs:
        for k, v in valores.items():
            if f"{{{{{k}}}}}" in p.text:
                p.text = p.text.replace(f"{{{{{k}}}}}", str(v))

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for k, v in valores.items():
                    if f"{{{{{k}}}}}" in cell.text:
                        cell.text = cell.text.replace(f"{{{{{k}}}}}", str(v))

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    word_name = f"cotizacion_{timestamp}.docx"
    pdf_name = f"cotizacion_{timestamp}.pdf"
    word_path = os.path.join(OUTPUT_DIR, word_name)
    pdf_path = os.path.join(OUTPUT_DIR, pdf_name)

    doc.save(word_path)

    try:
        convert(word_path, pdf_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando PDF: {e}")

    base_url = str(request.base_url).rstrip("/")
    return {
        "mensaje": "Documentos generados correctamente",
        "descargar_word": f"{base_url}/download/{word_name}",
        "descargar_pdf": f"{base_url}/download/{pdf_name}"
    }

# ============================================================
# Descargas
# ============================================================
@app.get("/download/{filename}")
def download_file(filename: str):
    file_path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return FileResponse(file_path, filename=filename)

@app.get("/")
def root():
    return {"mensaje": "Servicio TemplatePDF activo y listo."}