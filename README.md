# Motor de Notificaciones IA
### Red Social — Pipeline de Datos con Modelo de Machine Learning

Proyecto ITY1101 — Gestión de Datos para IA | Evaluación Parcial N°3

---

## Estructura del proyecto

```
motor-notificaciones-red-social/
├── notebooks/
│   └── motor_notificaciones_ia.ipynb   ← Notebook principal (EDA + entrenamiento + API)
├── src/
│   ├── ia/
│   │   ├── api_modelo.py               ← Servicio FastAPI (endpoint /predict)
│   │   ├── train_model.py              ← Script de entrenamiento standalone
│   │   └── modelo_notificaciones_rf.pkl← Artefacto del modelo (se genera al ejecutar)
│   ├── limpieza/
│   │   └── spark_cleaner.py            ← Pipeline de limpieza + llamada a la API IA
│   ├── ingesta/
│   │   └── kafka_producer.py
│   ├── validacion/
│   │   └── great_expectations_suite.py
│   └── carga/
│       ├── db_loader.py
│       └── init_db.sql                 ← Esquema con score_ia y prioridad_envio
├── data/
│   └── Dataset_Historico_Notificaciones_PowerBI.xlsx
├── logs/
│   ├── pipeline_execution.log
│   ├── metricas_modelo.png
│   ├── analisis_univariado.png
│   └── matriz_correlacion.png
├── docker/
│   └── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## PASO A PASO — Despliegue local

### Prerequisitos
- Python 3.10 o superior
- pip
- Git

### 1. Clonar o preparar el repositorio

```bash
# Si ya tienes el repositorio:
cd motor-notificaciones-red-social

# Si estás subiendo por primera vez:
git init
git remote add origin https://github.com/TU_USUARIO/motor-notificaciones-red-social.git
```

### 2. Crear entorno virtual e instalar dependencias

```bash
python -m venv venv

# Linux / macOS:
source venv/bin/activate

# Windows:
venv\Scripts\activate

pip install -r requirements.txt
```

### 3. Colocar el dataset

```bash
# Copia el Excel de Power BI en la carpeta data/
cp Dataset_Historico_Notificaciones_PowerBI.xlsx data/
```

### 4. Entrenar el modelo (opción A — notebook)

Abre Jupyter y ejecuta todas las celdas en orden:

```bash
jupyter lab
# Abre notebooks/motor_notificaciones_ia.ipynb
# Ejecuta: Kernel → Restart Kernel and Run All Cells
```

### 5. Entrenar el modelo (opción B — script terminal)

```bash
# Con el dataset real:
python src/ia/train_model.py --data data/Dataset_Historico_Notificaciones_PowerBI.xlsx

# Con dataset sintético (sin Excel):
python src/ia/train_model.py --synthetic --n 5000
```

Esto genera: `src/ia/modelo_notificaciones_rf.pkl`

### 6. Iniciar el servicio de la API del modelo

```bash
uvicorn src.ia.api_modelo:app --host 0.0.0.0 --port 8000 --reload
```

Verifica que funciona:

```bash
# Health check
curl http://localhost:8000/health

# Predicción de prueba
curl -X POST http://localhost:8000/predict \
     -H "Content-Type: application/json" \
     -d '{"tipo_notificacion":"mention","historico_ctr_usuario":0.82,"dias_inactivo":2}'

# Respuesta esperada:
# {"score_ia":0.8734,"prioridad_envio":"ALTA","tipo_notificacion":"mention","hora_evaluada":15,"timestamp_utc":"..."}
```

Documentación interactiva: http://localhost:8000/docs

### 7. Probar el pipeline completo (spark_cleaner.py)

Con la API corriendo en otra terminal:

```bash
python src/limpieza/spark_cleaner.py
```

### 8. Despliegue con Docker Compose (opcional)

```bash
# Primero asegúrate de haber entrenado el modelo (paso 4 o 5)
# El pkl debe existir en src/ia/

docker-compose up --build -d
docker-compose logs -f ia_service
```

Servicios disponibles:
- API IA:       http://localhost:8000
- Jupyter Lab:  http://localhost:8888
- PostgreSQL:   localhost:5432

---

## Flujo de datos con la integración IA

```
Kafka Producer
     ↓
spark_cleaner.py  →  POST /predict (api_modelo.py)
     ↓                      ↓
db_loader.py          score_ia + prioridad_envio
     ↓
PostgreSQL (notificaciones.score_ia, notificaciones.prioridad_envio)
     ↓
Power BI Dashboard
```

---

## Commits Git recomendados

```bash
# Después de entrenar el modelo y verificar que todo funciona:
git add .
git commit -m "feat: integrar modelo IA (Random Forest) al pipeline de notificaciones

- Agrega notebooks/motor_notificaciones_ia.ipynb con EDA completo,
  entrenamiento RF, métricas (accuracy/precision/recall/F1/ROC-AUC/Gini)
  y servicio FastAPI integrado
- Agrega src/ia/api_modelo.py: endpoint POST /predict para scoring
- Agrega src/ia/train_model.py: script de entrenamiento standalone
- Actualiza src/limpieza/spark_cleaner.py: llama al modelo antes
  de insertar cada notificación en DB
- Actualiza src/carga/init_db.sql: agrega columnas score_ia y
  prioridad_envio a tabla notificaciones
- Actualiza requirements.txt con nuevas dependencias
- Actualiza docker-compose.yml con servicio ia_service"

git push origin main
```

---

## Notas de seguridad y datos sensibles

- **`modelo_notificaciones_rf.pkl`** no contiene datos personales, solo parámetros del modelo.
- Los campos `usuario_id` y `remitente_id` son pseudoanonimizados (IDs internos).
- La API no expone datos de usuarios; solo recibe features agregadas.
- En producción: restringir `allow_origins` en CORS a los dominios del backend.
- Cumplimiento Ley 19.628 (Chile): los datos de comportamiento (CTR, inactividad)
  se procesan de forma agregada, sin identificar directamente a personas naturales.
