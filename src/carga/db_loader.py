import redis
import psycopg2
import json
import time
import logging
import os
from datetime import datetime

# Configuración de logs
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/pipeline_execution.log'),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

def cargar_redis(r, evento):
    for intento in range(3):
        try:
            # Generamos una clave única basada en destino y timestamp
            key = f"notif:{evento['usuario_destino']}:{int(time.time())}"
            # Guardamos con expiración de 24 horas (86400 seg)
            r.setex(key, 86400, json.dumps(evento))
            log.info(f"Redis OK → {key}")
            return True
        except Exception as e:
            log.warning(f"Redis intento {intento+1}/3 falló: {e}")
            time.sleep(1)
    return False

def cargar_postgres(conn, evento):
    for intento in range(3):
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO eventos (tipo, origen, destino, publicacion, ts) 
                       VALUES (%s, %s, %s, %s, %s)""",
                    (evento['tipo_evento'], evento['usuario_origen'],
                     evento['usuario_destino'], evento['publicacion_id'], evento['timestamp'])
                )
            conn.commit()
            log.info(f"PostgreSQL OK → {evento['tipo_evento']} | {evento['usuario_origen']}")
            return True
        except Exception as e:
            log.warning(f"PG intento {intento+1}/3 falló: {e}")
            conn.rollback() # Limpiar error de la transacción
            time.sleep(1)
    return False

if __name__ == '__main__':
    log.info("Iniciando proceso de carga...")
    
    try:
        # CONEXIÓN: Usamos host.docker.internal para conectar a los puertos mapeados en Windows
        r = redis.Redis(host='host.docker.internal', port=6379, socket_connect_timeout=5)
        
        conn = psycopg2.connect(
            "postgresql://admin:admin123@host.docker.internal:5432/notificaciones", 
            connect_timeout=5
        )
        
        # Crear tabla si no existe
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS eventos (
                    id SERIAL PRIMARY KEY, 
                    tipo TEXT, 
                    origen TEXT, 
                    destino TEXT, 
                    publicacion TEXT, 
                    ts TEXT
                )
            """)
        conn.commit()

        # Datos de prueba (Simulando lo que vendría del validador)
        eventos = [
            {"tipo_evento":"like","usuario_origen":"user_001","usuario_destino":"user_042","publicacion_id":"post_789","timestamp":"2025-05-07T10:32:01Z"},
            {"tipo_evento":"comentario","usuario_origen":"user_005","usuario_destino":"user_060","publicacion_id":"post_200","timestamp":"2025-05-07T10:34:00Z"},
        ]

        ok = err = 0
        for ev in eventos:
            # Intentar cargar en ambos destinos
            r_status = cargar_redis(r, ev)
            p_status = cargar_postgres(conn, ev)
            
            if r_status and p_status:
                ok += 1
            else:
                err += 1

        log.info(f"RESUMEN: {ok} exitosos | {err} errores")
        conn.close()

    except Exception as e:
        log.error(f"Error crítico de conexión: {e}")