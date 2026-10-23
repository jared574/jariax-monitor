# jariax-monitor

Dos tareas programadas de GitHub Actions para el Discord de Jariax:

- **monitor** (cada 5 min): revisa jariax.com, las entradas de Vangil y n8n. Avisa a #alertas solo cuando
  algo se cae o vuelve. El estado vive en `estado.json`.
- **resumen** (7:00 am de Monterrey): manda a #pendientes la agenda del dia (Google Calendar), los
  prospectos del foro #prospectos con 3+ dias sin movimiento y el conteo del pipeline.

Corre fuera del servidor de Hetzner a proposito: si el servidor se cae, el aviso sale igual.

Secretos del repo (Settings > Secrets > Actions): `DISCORD_WEBHOOK_ALERTAS`, `DISCORD_WEBHOOK_PENDIENTES`,
`DISCORD_BOT_TOKEN`, `GOOGLE_ICAL_URL` (direccion secreta en formato iCal del calendario).
Para correrlo a mano: pestaña Actions > el workflow > Run workflow.
