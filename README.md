# Codex Usage Watcher

Utilidad **no oficial** para Windows que revisa periódicamente la página de uso de Codex en ChatGPT y envía alertas al celular cuando tus límites se acercan al agotamiento o a su próximo reinicio.

> No utiliza una API oficial de OpenAI para obtener los límites. Lee la interfaz web de Codex desde un perfil dedicado de Brave, por lo que un cambio futuro en esa interfaz puede requerir actualizar el parser.

## ¿Para qué sirve?

Cuando usas Codex con frecuencia, revisar manualmente cuánto queda del límite de 5 horas o del límite semanal es incómodo. Codex Usage Watcher automatiza esa revisión y te avisa por **ntfy** sin dejar un navegador pesado funcionando permanentemente.

Por defecto puede avisar cuando:

- queda 20%, 10% o 5% del límite de 5 horas;
- queda 20%, 10% o 5% del límite semanal;
- faltan aproximadamente 60, 30 o 15 minutos para un reset conocido;
- detecta el comienzo de un nuevo ciclo por un salto grande del porcentaje restante;
- la sesión del perfil dedicado necesita atención.

## Ventajas

- **Bajo consumo en reposo:** entre lecturas no queda Brave ni Python residente.
- **Sin ventana molesta:** usa Brave normal para compatibilidad, pero Windows mantiene la ventana fuera de pantalla y oculta durante la captura.
- **Perfil separado:** no interfiere con tu Brave habitual.
- **Push al celular:** usa ntfy en Android o iPhone.
- **Topic único:** una instalación nueva genera automáticamente un topic largo y aleatorio.
- **Configuración local:** `config.json`, sesión de Brave y estados quedan en tu PC.
- **Sin fechas hardcodeadas:** intenta leer las fechas de reset directamente desde la interfaz.
- **Windows Task Scheduler:** la revisión se ejecuta automáticamente cada 10 minutos.

## Requisitos

- Windows 10 u 11.
- Conexión a Internet.
- Brave Browser.
- Python 3.11+ (el instalador intenta instalar Python y Brave mediante `winget` si faltan).
- Una cuenta de ChatGPT con acceso a Codex Usage.
- Opcional pero recomendado: app **ntfy** en el celular.

## Instalación rápida

1. Descarga o clona este repositorio.
2. Ejecuta `INSTALL_WINDOWS.bat`.
3. El instalador prepara Python, dependencias, configuración y perfil dedicado.
4. Si el perfil aún no está autenticado, Brave se abrirá **una sola vez**. Inicia sesión en ChatGPT, entra a Codex Usage, espera a ver tus porcentajes y cierra completamente esa ventana.
5. El instalador vuelve a probar la captura y crea la tarea `CodexUsageWatcher` cada 10 minutos.

Después de instalar, puedes revisar el estado con:

```text
STATUS_WINDOWS.bat
```

Y quitar la automatización con:

```text
UNINSTALL_WINDOWS.bat
```

## Configurar notificaciones en el celular con ntfy

ntfy tiene aplicaciones para Android e iOS. También puede utilizarse desde web. Documentación oficial: <https://docs.ntfy.sh/subscribe/phone/>.

### 1. Instala ntfy

- Android: Google Play, F-Droid o APK oficial.
- iPhone/iPad: App Store.

### 2. Obtén tu topic

En una instalación nueva, `INSTALL_WINDOWS.bat` genera un topic parecido a:

```text
codex-usage-8f30e3a2b9c44e30a57f7c3ad5d63c52
```

**Ese ejemplo no debes usarlo.** Tu instalación genera otro.

Si quieres consultar, cambiar o regenerar tu topic:

```text
CONFIGURE_NTFY.bat
```

### 3. Suscríbete desde el celular

Abre ntfy, agrega una suscripción y escribe **exactamente el mismo topic** que muestra el watcher. El servidor predeterminado es `https://ntfy.sh`.

Los topics de `ntfy.sh` no necesitan crearse previamente; al suscribirte simplemente eliges el nombre. ntfy recomienda usar nombres difíciles de adivinar porque los topics públicos deben tratarse como identificadores secretos. Documentación: <https://docs.ntfy.sh/>.

### 4. Prueba la notificación

Ejecuta `CONFIGURE_NTFY.bat` y selecciona **Enviar notificación de prueba**. Deberías recibir un push en el teléfono.

## Cómo funciona internamente

```text
Task Scheduler (cada 10 min)
          │
          ▼
      pythonw.exe
          │
          ▼
Brave normal + perfil dedicado
(ventana fuera de pantalla/oculta)
          │
          ▼
  Codex Settings → Usage
          │
          ▼
 Chrome DevTools Protocol
       en 127.0.0.1
          │
          ▼
   parser de porcentajes
          │
    ┌─────┴─────┐
    ▼           ▼
codex_usage   ntfy push
   .json       al celular
          │
          ▼
 Brave y Python terminan
```

La captura usa un puerto de DevTools dinámico y enlazado a `127.0.0.1`. No queda un servidor DevTools expuesto a la red.

## Archivos locales que NO se publican

Este repositorio **no contiene `config.json`**. Cada instalación crea el suyo a partir de `config.example.json`. También están ignorados:

```text
config.json
runtime/
.venv/
codex_usage.json
watcher_state.json
hidden_last_run.json
hidden_error_state.json
last_page_text.txt
```

No subas estos archivos a GitHub: `runtime/` contiene el perfil dedicado de Brave y `config.json` puede contener el topic o token de ntfy.

## Configuración avanzada

`config.example.json` contiene los valores predeterminados. Después de instalar, puedes editar tu `config.json` local.

Ejemplo de umbrales:

```json
{
  "alerts": {
    "five_hour_remaining_percent": [20, 10, 5],
    "weekly_remaining_percent": [20, 10, 5],
    "reset_minutes": [60, 30, 15]
  }
}
```

La zona horaria predeterminada es:

```json
"timezone": "local"
```

por lo que se utiliza la zona horaria configurada en Windows. También puedes indicar un identificador IANA compatible con Python.

Para ntfy:

```json
"ntfy": {
  "enabled": true,
  "server": "https://ntfy.sh",
  "topic": "TU_TOPIC_UNICO",
  "token": ""
}
```

El campo `token` es opcional y está pensado para servidores/configuraciones ntfy que requieran autenticación.

## Solución de problemas

### `PASS: 5h=... weekly=...`

La captura funciona correctamente.

### `stage: authentication`

La sesión del perfil dedicado expiró. Ejecuta nuevamente `INSTALL_WINDOWS.bat` o abre el perfil dedicado desde el flujo de instalación y vuelve a iniciar sesión.

### `stage: challenge` / “Un momento…”

El sitio está mostrando una verificación. El watcher no intenta saltársela. Abre el perfil dedicado de forma visible, completa lo que el sitio solicite y vuelve a probar.

### No llegan notificaciones

1. Ejecuta `CONFIGURE_NTFY.bat`.
2. Confirma que ntfy esté activado.
3. Verifica que el topic del PC y del teléfono sea idéntico.
4. Envía una notificación de prueba.
5. Revisa permisos de notificación/batería de ntfy en el teléfono.

### El PC está apagado

No habrá lecturas mientras el PC esté apagado. Esta herramienta es local; necesita que Windows esté encendido para ejecutar la tarea.

## Privacidad y seguridad

Lee [SECURITY.md](SECURITY.md). En resumen: no publiques tu `config.json`, topic/token de ntfy ni la carpeta `runtime/`. El perfil dedicado mantiene la sesión de ChatGPT en tu propio PC.

## Limitaciones

- Solo Windows.
- Actualmente está orientado a Brave.
- Depende de la estructura/texto de la interfaz de Codex Usage.
- No es un producto oficial de OpenAI ni de ntfy.
- No puede obtener datos nuevos con el PC apagado.

## Contribuir

Consulta [CONTRIBUTING.md](CONTRIBUTING.md). Issues y pull requests son bienvenidos.

## Licencia

MIT. Consulta [LICENSE](LICENSE).
