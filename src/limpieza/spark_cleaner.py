import pandas as pd
from datetime import datetime
import json

TIPOS_VALIDOS = {'like', 'comentario', 'seguidor'}

def limpiar_eventos(eventos_raw):
    df = pd.DataFrame(eventos_raw)
    original = len(df)

    # 1. Eliminar duplicados
    df = df.drop_duplicates(subset=['usuario_origen','usuario_destino','publicacion_id'])

    # 2. Descartar nulos obligatorios
    campos = ['tipo_evento','usuario_origen','usuario_destino','timestamp']
    df = df.dropna(subset=campos)

    # 3. Normalizar timestamps a ISO 8601
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True).dt.strftime('%Y-%m-%dT%H:%M:%SZ')

    # 4. Filtrar tipos inválidos
    df = df[df['tipo_evento'].isin(TIPOS_VALIDOS)]

    clean = len(df)
    print(f"v Limpieza: {original} eventos -> {clean} validos | {original-clean} descartados")
    return df

if __name__ == '__main__':
    # Datos de prueba con errores intencionales
    raw = [
        {"tipo_evento":"like","usuario_origen":"user_001","usuario_destino":"user_042","publicacion_id":"post_789","timestamp":"2025-05-07T10:32:01Z"},
        {"tipo_evento":"like","usuario_origen":"user_001","usuario_destino":"user_042","publicacion_id":"post_789","timestamp":"2025-05-07T10:32:01Z"},
        {"tipo_evento":None,"usuario_origen":"user_003","usuario_destino":"user_045","publicacion_id":"post_100","timestamp":"2025-05-07T10:33:00Z"},
        {"tipo_evento":"comentario","usuario_origen":"user_005","usuario_destino":"user_060","publicacion_id":"post_200","timestamp":"2025-05-07T10:34:00Z"},
        {"tipo_evento":"invalido","usuario_origen":"user_007","usuario_destino":"user_070","publicacion_id":"post_300","timestamp":"2025-05-07T10:35:00Z"},
    ]
    resultado = limpiar_eventos(raw)
    print(resultado[['tipo_evento','usuario_origen','usuario_destino','timestamp']])