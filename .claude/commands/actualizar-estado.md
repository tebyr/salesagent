# Comando: /actualizar-estado

Actualiza `docs/ESTADO_PROYECTO.md` y `docs/ROADMAP.md` con el estado real al cierre de la sesión actual.

## Pasos a ejecutar

### 1. Recopilar información de la sesión

Ejecuta estos comandos para obtener el contexto actualizado:

```bash
git log --oneline -8
git status
```

### 2. Calcular las nuevas versiones

**ESTADO_PROYECTO.md** — lee su tabla "Control de versiones" y determina el incremento:
- **Parche** (x.x.N): solo se corrigieron secciones, no hay componentes nuevos completados
- **Menor** (x.N.0): uno o más componentes cambiaron de estado (⬜→✅ o 🟡→✅)
- **Mayor** (N.0.0): se completó una fase entera del ROADMAP

**ROADMAP.md** — lee su tabla "Control de versiones" y determina el incremento:
- **Parche** (x.x.N): solo se actualizó el % de avance o notas, sin cambio de fase
- **Menor** (x.N.0): uno o más ítems de una fase pasaron a ✅
- **Mayor** (N.0.0): una fase completa se marcó como ✅ completada

### 3. Actualizar los documentos

#### 3a. `docs/ESTADO_PROYECTO.md`

Edita el archivo aplicando **solo los cambios que ocurrieron en esta sesión**:

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

#### 3b. `docs/ROADMAP.md`

Edita el archivo aplicando **solo los cambios que ocurrieron en esta sesión**:

**Siempre actualizar:**
- [ ] Tabla "Control de versiones": agregar nueva fila con versión, fecha de hoy y resumen de cambios
- [ ] `## Estado actual: ~XX%`: actualizar el porcentaje y el párrafo descriptivo
- [ ] "Frente activo": indicar cuál es la fase en curso actualmente

**Actualizar solo si hubo cambios:**
- [ ] Ítems de fase completados: cambiar columna Estado a ✅ y agregar hash del commit
- [ ] Fase completada: agregar prefijo `✅` al título de la fase y nota `(COMPLETADA — sesión N)`
- [ ] Promover siguiente fase: si la fase actual se cerró, marcar la siguiente como frente activo

### 4. Confirmar al usuario

Una vez actualizados ambos archivos, mostrar este resumen:

```
✅ ESTADO_PROYECTO.md actualizado a v[nueva versión]
✅ ROADMAP.md actualizado a v[nueva versión]

Cambios registrados:
  · [lista de lo que se actualizó]

Próxima sesión arrancará desde:
  · Avance: XX%
  · P1 pendiente: [N ítems]
  · Último commit: [hash]
```

### 5. Recordatorio final

```
💾 No olvides hacer commit de los documentos actualizados:
   git add docs/ESTADO_PROYECTO.md docs/ROADMAP.md
   git commit -m "docs: actualizar estado del proyecto vX.Y.Z"
```
