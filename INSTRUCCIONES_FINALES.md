# AGENTE COMPLETO - PROXIMOS PASOS

Tu agente de WhatsApp para Sutil Panaderia ya esta construido y listo para configurar.
Este archivo te guia paso a paso para ponerlo en produccion.

## 1. INSTALAR DEPENDENCIAS

Primero, asegúrate de tener Python 3.11+:
`
python3 --version
`

Instala las dependencias:
`
pip install -r requirements.txt
`

## 2. CONFIGURAR GOOGLE CLOUD (Google Sheets, Calendar, Gmail)

VER ARCHIVO: SETUP_GOOGLE_OPENAI.md

En resumen:
- Crea un proyecto en console.cloud.google.com
- Habilita: Google Sheets API, Calendar API, Gmail API
- Crea una Service Account
- Descarga el JSON y renómbralo como credentials.json
- Crea un Google Sheet con dos hojas: 'Clientes Recurrentes' y 'Pedidos'
- Comparte el Sheet y Calendar con el email de la Service Account

## 3. OBTENER OPENAI API KEY

Ve a platform.openai.com y crea una API Key (sk-...)

## 4. COMPLETAR TU .env

Copia .env.example como .env:
`
cp .env.example .env
`

Completa las variables:
`
ANTHROPIC_API_KEY=sk-ant-YOUR_KEY_HERE
OPENAI_API_KEY=sk-YOUR_OPENAI_KEY
GOOGLE_SERVICE_ACCOUNT_JSON=credentials.json
GOOGLE_SHEET_ID=PEGA_EL_ID_DE_TU_SHEET_AQUI
WHATSAPP_PROVIDER=twilio
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=whatsapp:+...
PORT=8000
ENVIRONMENT=development
DATABASE_URL=sqlite+aiosqlite:///./agentkit.db
`

## 5. PROBAR LOCALMENTE

`
# Test sin WhatsApp (chat en terminal)
python tests/test_local.py

# Escribir como cliente y ver las respuestas del agente
`

Prueba estos casos:
- Mensaje normal: 'Hola, tengo pan de hamburguesa?'
- Pedido grande (>=100): 'Quiero 100 panes de hamburguesa'
- Comando pausar: '#pausar'
- Comando reanudar: '#reanudar'

## 6. ARRANCAR EL SERVIDOR LOCAL

En otra terminal:
`
uvicorn agent.main:app --reload --port 8000
`

El servidor estara en: http://localhost:8000

## 7. CONECTAR CON TWILIO (opcional para probar)

Si quieres probar con WhatsApp real:
1. Ve a twilio.com y crea cuenta
2. Obtén las credenciales (Account SID, Auth Token, Phone Number)
3. Completa en tu .env
4. En Twilio, configura el webhook: http://YOUR_SERVER/webhook

## 8. DEPLOY A PRODUCCION (Railway)

Cuando estes listo:

1. Sube a GitHub:
`
git add .
git commit -m 'feat: agente panaderia completo'
git push
`

2. Ve a railway.app y conecta tu repositorio
3. Railway deployea automaticamente
4. Configura las variables de entorno en Railway (mismo .env)
5. Copia la URL publica de Railway
6. Configura webhook en Twilio apuntando a esa URL

## ARCHIVOS CLAVE

- agent/main.py → Servidor y procesamiento de mensajes
- agent/brain.py → Conexion con Claude AI
- agent/tools.py → Integraciones (Google, OpenAI, etc)
- agent/memory.py → Historial de conversaciones
- config/business.yaml → Datos de tu negocio
- config/prompts.yaml → Personalidad del agente

## COSAS IMPORTANTES

✓ El agente busca clientes recurrentes en Google Sheets
✓ Sugiere pedidos habituales automaticamente
✓ Calcula precios segun cantidad
✓ Registra pedidos en Sheets y Calendar
✓ Envia notificaciones a produccion
✓ Transcribe audios automaticamente
✓ Puede ser pausado/reanudado por el equipo

## PERSONALIZAR EL AGENTE

Puedes cambiar cosas sin tocar codigo:

- Tono: config/prompts.yaml
- Catalogo: config/business.yaml
- Herramientas: agent/tools.py
- System prompt: config/prompts.yaml

## COMANDOS UTILES

`
# Probar
python tests/test_local.py

# Arrancar servidor
uvicorn agent.main:app --reload --port 8000

# Build Docker
docker compose up --build

# Logs
docker compose logs -f agent
`

## TROUBLESHOOTING

Si ves errores, verifica:
1. credentials.json existe en la raiz
2. Variables de .env estan completas
3. Google Sheet compartido con el email de Service Account
4. OPENAI_API_KEY es valida
5. ANTHROPIC_API_KEY es valida

¡Listo! Tu agente de panaderia esta completo y listo para produccion.
