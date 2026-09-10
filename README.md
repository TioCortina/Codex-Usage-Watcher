# Codex Usage Watcher

Utilidad **no oficial** para Windows que revisa periódicamente la página de uso de Codex en ChatGPT y puede enviar alertas push al celular mediante **ntfy** cuando tus límites se acercan al agotamiento o a un reinicio.

No utiliza una API oficial de OpenAI para obtener los límites. Lee la interfaz web de Codex desde un **perfil dedicado** de un navegador Chromium compatible, por lo que cambios futuros en esa interfaz pueden requerir actualizar el parser.

## Navegadores compatibles

- **Brave**
- **Google Chrome**
- **Microsoft Edge**

El instalador intenta usar tu navegador predeterminado si es compatible. Si hay varios y no puede decidir, permite elegir durante la instalación.

Cada navegador utiliza un perfil dedicado independiente en `runtime/browser_profiles/`, por lo que no interfiere con tu perfil habitual.

## ¿Para qué sirve?

Cuando usas Codex con frecuencia, revisar manualmente cuánto queda del límite de 5 horas o del límite semanal es incómodo. Codex Usage Watcher automatiza esa revisión y te avisa por ntfy sin dejar un navegador pesado funcionando permanentemente.

Por defecto puede avisar cuando:

- queda 20%, 10% o 5% del límite de 5 horas;
- queda 20%, 10% o 5% del límite semanal;
- faltan aproximadamente 60, 30 o 15 minutos para un reset conocido;
- detecta el inicio de un nuevo ciclo;
- la sesión del perfil dedicado necesita atención.

## Ventajas

- **Bajo consumo:** entre lecturas no queda navegador ni Python residente.
- **Sin ventana molesta:** el navegador funciona en modo normal para compatibilidad, pero Windows lo oculta durante la captura.
- **Multinavegador:** Brave, Chrome y Edge.
- **Perfil separado por navegador:** no interfiere con tu navegación habitual.
- **Push al celular:** ntfy en Android, iPhone/iPad o web.
- **Topic único:** una instalación nueva puede generar automáticamente un topic largo y aleatorio.
- **Configuración local:** `config.json`, sesión y estados permanecen en tu PC.
- **Task Scheduler:** revisión automática cada 10 minutos.

## Requisitos

- Windows 10 u 11.
- Internet.
- Brave, Google Chrome o Microsoft Edge.
- Python 3.11+.
- Cuenta de ChatGPT con acceso a Codex Usage.
- Opcional pero recomendado: app **ntfy** en el celular.

`INSTALL_WINDOWS.bat` intenta instalar Python mediante `winget` si falta. Si no encuentra ningún navegador compatible, intenta instalar Microsoft Edge.

## Instalación

Descarga o clona el repositorio y ejecuta:

```text
INSTALL_WINDOWS.bat
```

El instalador prepara las dependencias, crea el `config.json` local, configura ntfy, detecta los navegadores instalados, selecciona uno, crea su perfil dedicado, prueba la captura invisible y finalmente instala `CodexUsageWatcher` cada 10 minutos.

Si el perfil todavía no está autenticado, el navegador elegido se abrirá **una sola vez** de forma visible. Inicia sesión en ChatGPT, abre Codex Usage, espera a ver los porcentajes y cierra completamente esa ventana.

## Cambiar de navegador

Ejecuta:

```text
CONFIGURE_BROWSER.bat
```

Puedes elegir cualquiera de los navegadores compatibles instalados. Después ejecuta `INSTALL_WINDOWS.bat` para autenticar el perfil dedicado del nuevo navegador y validar la captura.

## Configurar ntfy en el celular

Documentación oficial: <https://docs.ntfy.sh/>.

1. Instala ntfy en Android o iPhone/iPad.
2. Ejecuta `CONFIGURE_NTFY.bat`.
3. Copia el topic que muestra el watcher.
4. En la app ntfy crea una suscripción usando **exactamente el mismo topic**.
5. Usa `https://ntfy.sh` salvo que tengas un servidor propio.
6. Desde `CONFIGURE_NTFY.bat`, envía una notificación de prueba.

Ejemplo ilustrativo:

```text
codex-usage-8f30e3a2b9c44e30a57f7c3ad5d63c52
```

No uses ese ejemplo: cada instalación debe generar su propio topic.

En `ntfy.sh`, trata un topic público como un identificador secreto: usa uno largo y difícil de adivinar.

## Cómo funciona

```text
Task Scheduler (cada 10 min)
          |
          v
     pythonw.exe
          |
          v
Brave / Chrome / Edge
  + perfil dedicado
  + ventana oculta
          |
          v
Codex Settings -> Usage
          |
          v
Chrome DevTools Protocol
   solo en 127.0.0.1
          |
          v
   parser de porcentajes
      /           \
     v             v
codex_usage.json   ntfy push
          |
          v
navegador y Python terminan
```

## Archivos locales que NO se publican

El repositorio **no contiene `config.json`**. Cada instalación crea el suyo desde `config.example.json`.

También están ignorados:

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

`runtime/browser_profiles/` contiene los perfiles dedicados y puede conservar sesiones autenticadas. No lo publiques.

## Configuración avanzada

### Navegador

```json
"browser": {
  "preferred": "auto",
  "selected": "",
  "profile_root": "runtime/browser_profiles",
  "profile_dir": ""
}
```

`selected` puede ser `brave`, `chrome` o `edge`.

### Alertas

```json
"alerts": {
  "five_hour_remaining_percent": [20, 10, 5],
  "weekly_remaining_percent": [20, 10, 5],
  "reset_minutes": [60, 30, 15]
}
```

### ntfy

```json
"ntfy": {
  "enabled": true,
  "server": "https://ntfy.sh",
  "topic": "TU_TOPIC_UNICO",
  "token": ""
}
```

## Solución de problemas

### `PASS [Google Chrome]: 5h=... weekly=...`

La captura funciona. El texto entre corchetes indica qué navegador está usando.

### `stage: authentication`

Ejecuta `INSTALL_WINDOWS.bat` y vuelve a iniciar sesión en el perfil dedicado cuando se abra el navegador.

### `stage: challenge` / “Un momento…”

El watcher no intenta saltarse una verificación. Ejecuta `INSTALL_WINDOWS.bat`, completa la verificación visible y vuelve a probar.

### Quiero usar otro navegador

Ejecuta `CONFIGURE_BROWSER.bat` y después `INSTALL_WINDOWS.bat`.

### No llegan notificaciones

Ejecuta `CONFIGURE_NTFY.bat`, revisa que el topic del PC y celular coincida exactamente y envía una prueba.

### El PC está apagado

No habrá lecturas. Esta es una herramienta local.

## Privacidad y seguridad

Consulta [SECURITY.md](SECURITY.md). No publiques `config.json`, `runtime/`, cookies, tokens ni logs con información sensible.

## Limitaciones

- Solo Windows.
- Navegadores implementados: Brave, Google Chrome y Microsoft Edge.
- Depende de la estructura/texto actual de Codex Usage.
- No es un producto oficial de OpenAI, Brave, Google, Microsoft ni ntfy.
- No obtiene datos nuevos con el PC apagado.

## Contribuir

Consulta [CONTRIBUTING.md](CONTRIBUTING.md).

## Licencia

MIT. Consulta [LICENSE](LICENSE).
