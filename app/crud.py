from sqlalchemy.orm import Session
from . import models
from . import schemas

def crear_estacion(estacion: schemas.EstacionCreate, db: Session):
    nueva_estacion = models.EstacionDB(id=estacion.id, nombre=estacion.nombre, ubicacion=estacion.ubicacion)
    db.add(nueva_estacion)
    db.commit()
    db.refresh(nueva_estacion)
    return {"msj": "Estación guardada en DB", "data": nueva_estacion}

def registrar_lectura(lectura: schemas.LecturaCreate, db: Session):
    estacion = db.query(models.EstacionDB).filter(models.EstacionDB.id == lectura.estacion_id).first()
    if not estacion:
        raise HTTPException(status_code=404, detail="Estación no existe")
    nueva_lectura = models.LecturaDB(valor=lectura.valor,
    estacion_id=lectura.estacion_id)
    db.add(nueva_lectura)
    db.commit()
    return {"status": "Lectura guardada en DB"}

def listar_estaciones(db: Session):
    estaciones = db.query(models.EstacionDB).all()
    return estaciones

def obtener_riesgo(id: int, db: Session):
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

def obtener_historial(id: int, db: Session):
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

def obtener_historial_stats(db: Session):
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