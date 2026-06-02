# CONFIGURACION DE INTEGRACIONES

## 1. Google Sheets, Calendar y Gmail

1. Ve a console.cloud.google.com
2. Crea un proyecto nuevo
3. Habilita: Google Sheets API, Calendar API, Gmail API
4. Crea una Service Account y descarga el JSON
5. Renombra como credentials.json
6. Crea un Google Sheet con hojas: 'Clientes Recurrentes' y 'Pedidos'
7. Comparte el Sheet y Calendar con el email de la Service Account
8. Copia el ID del Sheet a GOOGLE_SHEET_ID en .env

## 2. OpenAI Whisper

1. Ve a platform.openai.com
2. Crea una API Key
3. Copia en OPENAI_API_KEY en .env

## 3. Variables de entorno

Completa tu .env con todas las claves obtenidas arriba.
