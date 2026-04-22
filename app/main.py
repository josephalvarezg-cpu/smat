from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
import models
import schemas
import crud
from database import engine, get_db
from app.auth import crear_token_acceso, obtener_identidad_actual

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="SMAT - Sistema de Monitoreo de Alerta Temprana",
    description="""
    API robusta para la gestión y monitoreo de desastres naturales.
    Permite la telemetría de sensores en tiempo real y el cálculo de niveles de riesgo.
    **Entidades principales:**
    * **Estaciones:** Puntos de monitoreo físico.
    * **Lecturas:** Datos capturados por sensores.
    * **Riesgos:** Análisis de criticidad basado en umbrales.
    """,
    version="1.0.0",
    terms_of_service="http://unmsm.edu.pe/terms/",
    contact={
    "name": "Soporte Técnico SMAT - FISI",
    "url": "http://fisi.unmsm.edu.pe",
    "email": "desarrollo.smat@unmsm.edu.pe",
    },
    license_info={
    "name": "Apache 2.0",
    "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    },
)

@app.post("/token", tags=["Seguridad"])
    async def login_para_obtener_token():
    # En la Unidad II esto validará contra la tabla de usuarios
    return {"access_token": crear_token_acceso({"sub": "admin_smat"}), "token_type": "bearer"}

# Endpoint Protegido: Solo accesible con Token válido
@app.post(
    "/estaciones/",
    status_code=201,
    tags=["Gestión de Infraestructura"],
    summary="Registrar una nueva estación de monitoreo",
    description="Inserta una estación física (ej. río, volcán, zona sísmica) en la base de datos relacional."
)
def crear_estacion(
    estacion: schemas.EstacionCreate,
    db: Session = Depends(get_db),
    usuario: str = Depends(obtener_identidad_actual) # PROTECCIÓN JWT
):
    return crud.crear_estacion(db=db, estacion=estacion)

@app.post(
    "/lecturas/",
    status_code=201,
    tags=["Telemetría de Sensores"],
    summary="Recibir datos de telemetría",
    description="Recibe el valor capturado por un sensor y lo vincula a una estación existente mediante su ID."
)
def registrar_lectura(lectura: schemas.LecturaCreate, db: Session = Depends(get_db)):
    estacion = db.query(models.EstacionDB).filter(models.EstacionDB.id == lectura.estacion_id).first()
    if not estacion:
        raise HTTPException(status_code=404, detail="Estación no existe")
    nueva_lectura = models.LecturaDB(valor=lectura.valor,
    estacion_id=lectura.estacion_id)
    db.add(nueva_lectura)
    db.commit()
    return {"status": "Lectura guardada en DB"}

@app.get(
    "/estaciones/",
    response_model=List[schemas.EstacionCreate],
    tags=["Gestión de Infraestructura"],
    summary="Listar las estaciones de monitoreo",
    description="Obtiene la lista de las estaciones existentes en la base de datos relacional"
)
def listar_estaciones(db: Session = Depends(get_db)):
    estaciones = db.query(models.EstacionDB).all()
    return estaciones

@app.get(
    "/estaciones/{id}/riesgo",
    tags=["Análisis de Riesgo"],
    summary="Evaluar nivel de peligro actual",
    description="Analiza la última lectura recibida de una estación y determina si el estado es NORMAL, ALERTA o PELIGRO."
)
async def obtener_riesgo(id: int, db: Session = Depends(get_db)):
    estacion = db.query(models.EstacionDB).filter(models.EstacionDB.id == id).first()
    if not estacion:
        raise HTTPException(status_code = 404, detail="Estación no encontrada")
    lecturas = db.query(models.LecturaDB).filter(models.LecturaDB.estacion_id == id).all()
    if not lecturas:
        return {"id": id, "nivel": "SIN DATOS", "valor": 0}
    ultima_lectura = lecturas[-1].valor
    if ultima_lectura > 20.0:
        nivel = "PELIGRO"
    elif ultima_lectura > 10.0:
        nivel = "ALERTA"
    else:
        nivel = "NORMAL"
    return {"id": id, "valor": ultima_lectura, "nivel": nivel}

@app.get(
    "/estaciones/{id}/historial",
    tags=["Reportes Históricos"],
    summary="Mostrar el histórico, conteo y el promedio de lecturas",
    description="Muestra el histórico de las lecturas vinculadas a una estación existente y realiza el cálculo del promedio y conteo de lecturas del histórico mostrado"
)
async def obtener_historial(id: int, db: Session = Depends(get_db)):
    estacion = db.query(models.EstacionDB).filter(models.EstacionDB.id == id).first()
    if not estacion:
        raise HTTPException(status_code = 404, detail="Estación no encontrada")
    lecturas = db.query(models.LecturaDB).filter(models.LecturaDB.estacion_id == id).all()
    if len(lecturas) > 0:
        promedio = sum(l.valor for l in lecturas) / len(lecturas)
    else:
        promedio = 0.0
    return {
        "estacion_id": id,
        "lecturas": lecturas,
        "conteo": len(lecturas),
        "promedio": round(promedio, 2)
    }    

@app.get(
    "/estaciones/criticos",
    tags=["Auditoria"],
    summary="",
    description=""
)
def obtener_criticos():
    raise HTTPException(status_code = 501, detail="No implementado")

@app.get(
    "/estaciones/stats",
    tags=["Reportes Ejecutivos"],
    summary="Mostrar el conteo de estaciones, lecturas y la estacion en punto crítico máximo",
    description="Muestra el conteo de las estaciones monitoreadas y del histórico de lecturas totales; y muestra la estación con el valor de lectura mas alto (Punto crítico máximo)"
)
def obtener_historial_stats(db: Session = Depends(get_db)):
    # Lista de todas las estaciones
    estaciones = db.query(models.EstacionDB).all()
    # Query de la tabla LecturaDB
    lecturas_query = db.query(models.LecturaDB)
    # Lista de todas las lecturas
    lecturas = lecturas_query.all()
    # Objeto con la lectura mas alta
    lectura_critica = lecturas_query.order_by(desc(models.LecturaDB.valor)).first()
    if not lectura_critica:
        raise HTTPException(status_code = 404, detail="Información de lectura crítica no encontrada")
    else:
        return {
            "total_estaciones": len(estaciones),
            "total_lecturas": len(lecturas),
            "estacion_critica": lectura_critica.estacion_id
        }