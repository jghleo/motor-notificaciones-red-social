# Auditoría de Seguridad — Motor de Notificaciones IA

## Datos sensibles identificados
- `usuario_id` y `remitente_id`: identificadores de personas naturales
- `contenido`: texto libre que puede contener menciones a terceros
- `historico_ctr_usuario`: perfil de comportamiento individual

## Medidas de protección implementadas
- Los IDs son pseudoanónimos (no se almacena nombre ni email en el pipeline)
- La API no expone datos de usuarios, solo recibe features agregadas
- CORS restringido (se debe limitar a dominios del backend en producción)
- El modelo .pkl no contiene datos personales, solo parámetros matemáticos

## Roles de acceso
| Rol | Acceso permitido |
|-----|-----------------|
| pipeline_user | Solo INSERT en tabla notificaciones |
| analista_bi | Solo SELECT en vistas agregadas |
| admin | Acceso total — solo en entorno local |

## Cumplimiento Ley 19.628 (Chile)
- Los datos se procesan con finalidad legítima (mejorar experiencia de usuario)
- No se transfieren a terceros sin consentimiento
- El usuario puede solicitar eliminación de su historial
- Los datos de comportamiento se procesan de forma agregada