from kafka import KafkaProducer
import json, time, random
from datetime import datetime, timezone

producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

tipos = ['like', 'comentario', 'seguidor']
for i in range(20):
    evento = {
        "tipo_evento": random.choice(tipos),
        "usuario_origen": f"user_{random.randint(1,50):03d}",
        "usuario_destino": f"user_{random.randint(51,100):03d}",
        "publicacion_id": f"post_{random.randint(100,999)}",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    producer.send('notificaciones', evento)
    print(f"[{i+1:02d}] Evento enviado: {evento['tipo_evento']} | {evento['usuario_origen']} -> {evento['usuario_destino']}")
    time.sleep(0.3)

producer.flush()
print("v 20 eventos enviados exitosamente")
