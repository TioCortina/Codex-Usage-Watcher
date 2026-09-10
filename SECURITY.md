# Security

Codex Usage Watcher utiliza un perfil dedicado del navegador seleccionado para acceder a la página de Codex Usage.

## No publiques

- `config.json`
- `runtime/`
- `.venv/`
- cookies o datos de sesión
- `codex_usage.json`
- `watcher_state.json`
- `hidden_last_run.json`
- `hidden_error_state.json`
- `last_page_text.txt`
- topics privados o tokens de ntfy

`runtime/browser_profiles/` puede contener sesiones autenticadas de ChatGPT para Brave, Google Chrome o Microsoft Edge.

## DevTools

La captura abre Chrome DevTools Protocol únicamente sobre `127.0.0.1` y utiliza un puerto dinámico. El navegador termina después de cada lectura.

## ntfy

En servidores públicos como `ntfy.sh`, considera el topic un identificador secreto y usa nombres largos y aleatorios.

## Reportar vulnerabilidades

No publiques credenciales, cookies ni tokens en issues. Elimina datos sensibles de logs o capturas antes de compartirlos.
