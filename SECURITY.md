# Seguridad y privacidad

Codex Usage Watcher es una utilidad local y no oficial.

## Datos que permanecen en el PC

- `config.json` (incluye el topic de ntfy y, si se configura, un token).
- `runtime/brave_codex_profile/` (perfil dedicado de Brave con la sesión de ChatGPT).
- `codex_usage.json`, `hidden_last_run.json` y otros archivos de estado.

Todos estos archivos están ignorados por Git y **no deben publicarse**.

## ntfy

Los topics públicos de `ntfy.sh` funcionan como identificadores compartidos: cualquiera que conozca un topic puede, en principio, acceder a él. Usa un nombre largo y aleatorio y no lo publiques. El instalador genera uno automáticamente. Para mayor control puedes usar un servidor ntfy propio o un token compatible editando `config.json`.

## Sesión de ChatGPT

La utilidad no pide ni almacena tu contraseña directamente. La autenticación queda dentro del perfil dedicado de Brave. Protege tu cuenta de Windows y no compartas la carpeta `runtime/`.

## Reportar problemas

Antes de adjuntar logs o JSON a un issue, elimina topics, tokens, rutas personales y cualquier dato de sesión.
