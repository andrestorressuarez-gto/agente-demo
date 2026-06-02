# CAMBIOS APLICADOS AL AGENTE - Sutil Panaderia

## Resumen
Se ha transformado el agente basico en un sistema completo y profesional
para la panaderia Sutil con integraciones Google, OpenAI Whisper, y
gestion automatica de pedidos.

## Cambios principales

### 1. DEPENDENCIAS ACTUALIZADAS (requirements.txt)
+ google-auth>=2.27.0
+ google-auth-oauthlib>=1.2.0
+ google-auth-httplib2>=0.2.0
+ google-api-python-client>=2.100.0
+ openai>=1.3.0

### 2. CONFIGURACION DE NEGOCIO (config/business.yaml)
- Actualizado con catalogo completo de Sutil Panaderia
- Pan de Hamburguesa (5 variedades): Clasico, Integral, Brioche, Ajonjoli, Carbon Activo
- Pan para Perro (Hotdog)
- Pan Sandwich
- Precios por presentacion: unidad, paquete x6, paquete x12, mayor a 50
- Email de produccion para notificaciones

### 3. SYSTEM PROMPT MEJORADO (config/prompts.yaml)
- Flujo completo de atencion a cliente recurrente
- Verificacion automatica en Google Sheets
- Sugerencia de pedido habitual
- Manejo de audios (Whisper)
- Escalacion a humanos
- Comandos especiales (#pausar, #reanudar)
- Tono natural y conversacional (sin negrillas excesivas)

### 4. HERRAMIENTAS AVANZADAS (agent/tools.py)
REESCRITO COMPLETAMENTE con:
- Google Sheets: buscar clientes recurrentes, registrar pedidos
- Google Calendar: crear eventos de entrega
- Gmail: enviar notificaciones a equipo de produccion
- OpenAI Whisper: transcribir audios a texto
- Calculo automatico de precios segun cantidad
- Gestion de carritos en memoria
- Pausa/reanudacion de chats

### 5. SERVIDOR MEJORADO (agent/main.py)
- Manejo de audios (descarga y transcripcion con Whisper)
- Procesamiento de comandos #pausar y #reanudar
- Consulta automatica a Google Sheets antes de saludar
- Inyeccion de contexto de cliente recurrente
- Deteccion de chats pausados

### 6. BRAIN MEJORADO (agent/brain.py)
- Manejo correcto de mensajes de sistema
- Inyeccion de contexto de cliente en el system prompt
- Mejor logging de uso de tokens

### 7. PROVIDER ACTUALIZADO (agent/providers/twilio.py)
- Soporte para archivos de audio
- Extraccion de URL de media desde webhook

### 8. ARCHIVOS DE CONFIGURACION
- .env.example: variables completas para Google, OpenAI, Twilio
- .gitignore: actualizado para permitir que code vaya a GitHub
- SETUP_GOOGLE_OPENAI.md: guia paso a paso de configuracion

## FLUJO NUEVO DE ATENCION

1. CLIENTE ESCRIBE por WhatsApp
2. SERVIDOR recibe webhook
3. SI ES AUDIO: transcribir con Whisper
4. CONSULTAR Google Sheets: buscar si es cliente recurrente
5. SI EXISTE: saludarlo por nombre y sugerir pedido habitual
6. PROCESAR pedido: confirmar producto, tipo, cantidad
7. CALCULAR precio automaticamente
8. SI < 100 unidades: informar entrega en 2 dias habiles
9. SI >= 100 unidades: escalar a equipo para confirmar fecha
10. REGISTRAR en Google Sheets
11. CREAR evento en Google Calendar
12. ENVIAR notificacion por Gmail a produccion
13. ENVIAR respuesta por WhatsApp

## COEXISTENCIA CON HUMANOS

#pausar: El equipo escribe este comando para pausar el chat
         El agente deja de responder, un humano lo atiende

#reanudar: Cuando el humano termina, escribe esto
          El agente reanuda atencion automatica

Si agente no puede resolver: escala a equipo con registro en Sheets

## PROXIMO PASO

Antes de usar en produccion:

1. Descargar credentials.json de Google Cloud Service Account
2. Colocar en raiz del proyecto como: credentials.json
3. Crear Google Sheet con hojas: 'Clientes Recurrentes' y 'Pedidos'
4. Compartir Sheet con el email del Service Account
5. Crear Google Calendar y compartir
6. Obtener ID del Sheet y colocar en .env como GOOGLE_SHEET_ID
7. Obtener OpenAI API Key y colocar en .env como OPENAI_API_KEY
8. Completar variables de Twilio en .env
9. Completar ANTHROPIC_API_KEY en .env

Ver archivo: SETUP_GOOGLE_OPENAI.md para instrucciones detalladas

## ARCHIVOS MODIFICADOS

✓ requirements.txt
✓ config/business.yaml
✓ config/prompts.yaml
✓ agent/tools.py (reescrito completamente)
✓ agent/main.py
✓ agent/brain.py
✓ agent/providers/twilio.py
✓ .env.example (creado)
✓ .gitignore
✓ SETUP_GOOGLE_OPENAI.md (creado)

## ARCHIVOS SIN CAMBIOS (compatibles)

- agent/memory.py
- agent/__init__.py
- tests/test_local.py
- Dockerfile
- docker-compose.yml
- agent/providers/base.py
- agent/providers/__init__.py

Todo listo para produccion!
