# Sales Agent SaaS — Instrucciones de sesión

## Arranque automático

Al iniciar cada sesión, lee el documento de estado del proyecto importado a continuación y presenta al usuario un resumen con este formato exacto:

```
📍 Sales Agent SaaS — Sesión activa
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Versión estado : [versión del ESTADO_PROYECTO.md]
Avance global  : ~72%  (actualizar si cambió)
Último commit  : [hash y mensaje del último commit en git]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Pendiente P1:
  · [listar ítems P1 no completados del ESTADO_PROYECTO.md]

¿Por dónde continuamos?
```

Si el usuario dice "actualiza el estado del proyecto" o "/actualizar-estado", ejecuta el comando definido en `.claude/commands/actualizar-estado.md`.

---

## Estado del proyecto

@docs/ESTADO_PROYECTO.md

---

## Reglas de trabajo

### Flujo obligatorio antes de ejecutar cualquier cambio
1. Mostrar resumen del plan (qué archivos se tocan, qué hace cada cambio)
2. Esperar confirmación explícita del usuario ("autorizado", "sí", "procede")
3. Solo entonces ejecutar

### Commits
- **NUNCA** hacer commits automáticamente
- Solo hacer commit cuando el usuario lo pida explícitamente
- Nunca usar `--no-verify` ni saltarse hooks

### Idioma
- Responder siempre en **español colombiano**
- Los comentarios en código pueden ser en español
- Los nombres de variables y funciones siguen las convenciones del proyecto (inglés)

### Decisiones técnicas
- Las decisiones listadas en la sección 3 del ESTADO_PROYECTO.md **no se reabren**
- Si hay una razón técnica fuerte para cambiar una decisión, plantearla antes de implementar

### Al terminar la sesión
- Recordar al usuario ejecutar `/actualizar-estado` antes de cerrar
