"""
api_modelo.py — Servicio REST del Motor de Notificaciones IA
=============================================================
Expone el modelo Random Forest entrenado como un endpoint HTTP.
El spark_cleaner.py y kafka_producer.py del pipeline llaman a
POST /predict para enriquecer cada notificación con un score_ia
antes de almacenarla o enviarla.

Uso (producción local):
    uvicorn src.ia.api_modelo:app --host 0.0.0.0 --port 8000 --reload

Uso (Docker):
    Definido en docker-compose.yml bajo el servicio "ia_service".
"""

import datetime
import os
import pathlib

import joblib
import numpy as np
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

# ── Ruta al artefacto del modelo ──────────────────────────────────────────────
BASE_DIR   = pathlib.Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "modelo_notificaciones_rf.pkl"

if not MODEL_PATH.exists():
    raise FileNotFoundError(
        f"Modelo no encontrado en {MODEL_PATH}.\n"
        "Ejecuta primero el notebook notebooks/motor_notificaciones_ia.ipynb "
        "para entrenar y guardar el modelo."
    )

modelo = joblib.load(MODEL_PATH)

# ── Mapa de tipos de notificación → código numérico ───────────────────────────
MAPA_TIPO = {"like": 0, "comment": 1, "follow": 2, "mention": 3}

# ── Aplicación FastAPI ────────────────────────────────────────────────────────
app = FastAPI(
    title="Motor de Notificaciones — API de IA",
    description=(
        "Recibe los atributos de una notificación y retorna un score_ia (0.0–1.0) "
        "que indica la probabilidad de que el usuario interactúe con ella, "
        "junto con una prioridad operativa (ALTA / MEDIA / BAJA)."
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],    # Restringir en producción real
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ── Esquemas de entrada y salida ──────────────────────────────────────────────

class PayloadNotificacion(BaseModel):
    """Datos de entrada enviados por el pipeline antes de despachar una notificación."""

    tipo_notificacion: str = Field(
        ...,
        description="Tipo de notificación: like | comment | follow | mention",
        json_schema_extra={"example": "mention"},
    )
    historico_ctr_usuario: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="CTR histórico del usuario destinatario (valor entre 0.0 y 1.0).",
        json_schema_extra={"example": 0.78},
    )
    dias_inactivo: int = Field(
        ...,
        ge=0,
        le=365,
        description="Días transcurridos desde la última actividad del usuario.",
        json_schema_extra={"example": 3},
    )
    hora_del_dia: int | None = Field(
        None,
        ge=0,
        le=23,
        description=(
            "Hora UTC de envío (0–23). "
            "Si se omite, se usa la hora UTC actual del servidor."
        ),
        json_schema_extra={"example": 15},
    )

    @field_validator("tipo_notificacion")
    @classmethod
    def tipo_valido(cls, v: str) -> str:
        v_lower = v.strip().lower()
        if v_lower not in MAPA_TIPO:
            raise ValueError(
                f"tipo_notificacion inválido: '{v}'. "
                f"Valores aceptados: {list(MAPA_TIPO.keys())}"
            )
        return v_lower


class RespuestaPrediccion(BaseModel):
    """Respuesta del modelo para una notificación individual."""

    score_ia: float = Field(..., description="Probabilidad de interacción (0.0–1.0).")
    prioridad_envio: str = Field(..., description="ALTA | MEDIA | BAJA")
    tipo_notificacion: str
    hora_evaluada: int
    timestamp_utc: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health", tags=["Monitoreo"])
def health_check() -> dict:
    """Verificación de disponibilidad del servicio."""
    return {
        "status": "ok",
        "modelo": "motor_notificaciones_rf_v2",
        "timestamp_utc": datetime.datetime.utcnow().isoformat(),
    }


@app.post("/predict", response_model=RespuestaPrediccion, tags=["Predicción"])
def predecir_engagement(data: PayloadNotificacion) -> RespuestaPrediccion:
    """
    Predice la probabilidad de que el usuario destinatario interactúe
    con la notificación entrante.

    Retorna:
    - **score_ia**: float entre 0.0 y 1.0.
    - **prioridad_envio**: ALTA (≥0.75) | MEDIA (≥0.40) | BAJA (<0.40).

    Reglas de negocio de prioridad:
    - ALTA  → notificación despachada inmediatamente por Kafka.
    - MEDIA → encolada en la ventana de envío óptimo.
    - BAJA  → almacenada; enviada solo si el usuario tiene actividad posterior.
    """
    try:
        cod_tipo  = MAPA_TIPO[data.tipo_notificacion]
        hora      = (
            data.hora_del_dia
            if data.hora_del_dia is not None
            else datetime.datetime.utcnow().hour
        )

        import pandas as _pd
        features  = _pd.DataFrame(
            [[cod_tipo, data.historico_ctr_usuario, data.dias_inactivo, hora]],
            columns=["tipo_cod", "historico_ctr_usuario", "dias_inactivo", "hora_del_dia"],
        )
        prob_click = float(modelo.predict_proba(features)[0][1])

        if   prob_click >= 0.75: prioridad = "ALTA"
        elif prob_click >= 0.40: prioridad = "MEDIA"
        else:                    prioridad = "BAJA"

        return RespuestaPrediccion(
            score_ia          = round(prob_click, 4),
            prioridad_envio   = prioridad,
            tipo_notificacion = data.tipo_notificacion,
            hora_evaluada     = hora,
            timestamp_utc     = datetime.datetime.utcnow().isoformat(),
        )

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ── Punto de entrada directo ───────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run(
        "api_modelo:app",
        host="0.0.0.0",
        port=int(os.getenv("IA_SERVICE_PORT", 8000)),
        reload=False,
        log_level="info",
    )
