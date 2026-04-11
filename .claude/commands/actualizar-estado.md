# Comando: /actualizar-estado

Actualiza `docs/ESTADO_PROYECTO.md` con el estado real al cierre de la sesión actual.

## Pasos a ejecutar

### 1. Recopilar información de la sesión

Ejecuta estos comandos para obtener el contexto actualizado:

```bash
git log --oneline -8
git status
```

### 2. Calcular la nueva versión

Lee la tabla de "Control de versiones" en `docs/ESTADO_PROYECTO.md` y determina el incremento:
- **Parche** (x.x.N): solo se corrigieron secciones, no hay componentes nuevos completados
- **Menor** (x.N.0): uno o más componentes cambiaron de estado (⬜→✅ o 🟡→✅)
- **Mayor** (N.0.0): se completó una fase entera del ROADMAP

### 3. Actualizar el documento

Edita `docs/ESTADO_PROYECTO.md` aplicando **solo los cambios que ocurrieron en esta sesión**:

**Siempre actualizar:**
- [ ] Tabla "Control de versiones": agregar nueva fila con versión, fecha de hoy, número de sesión y resumen de cambios
- [ ] "Último commit" en el Resumen ejecutivo: hash + mensaje del commit más reciente
- [ ] "Avance global %": recalcular si cambiaron componentes
- [ ] Tabla de "Historial de sesiones": agregar fila con la sesión actual

**Actualizar solo si hubo cambios:**
- [ ] Mapa de componentes: cambiar estado (⬜→✅, 🟡→✅) de los componentes completados
- [ ] Trabajo pendiente: mover ítems completados, agregar nuevos si se detectaron durante la sesión
- [ ] Decisiones técnicas: agregar nuevas decisiones tomadas durante la sesión
- [ ] Convenciones y patrones: agregar nuevos patrones establecidos

### 4. Confirmar al usuario

Una vez actualizado el archivo, mostrar este resumen:

```
✅ ESTADO_PROYECTO.md actualizado a v[nueva versión]

Cambios registrados:
  · [lista de lo que se actualizó]

Próxima sesión arrancará desde:
  · Avance: XX%
  · P1 pendiente: [N ítems]
  · Último commit: [hash]
```

### 5. Recordatorio final

```
💾 No olvides hacer commit del documento actualizado:
   git add docs/ESTADO_PROYECTO.md docs/ROADMAP.md
   git commit -m "docs: actualizar estado del proyecto vX.Y.Z"
```
