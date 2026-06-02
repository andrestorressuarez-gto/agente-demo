# agent/main.py — Servidor FastAPI + Webhook de WhatsApp
"""
Servidor principal del agente de WhatsApp con soporte para:
- Audios (transcripción con Whisper)
- Comandos #pausar / #reanudar
- Integración Google Sheets (CRM)
- Notificaciones automáticas
"""

import os
import logging
import tempfile
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv

from agent.brain import generar_respuesta
from agent.memory import inicializar_db, guardar_mensaje, obtener_historial
from agent.providers import obtener_proveedor
from agent.tools import (
    buscar_cliente_recurrente, transcribir_audio, esta_pausado,
    pausar_chat, reanudar_chat
)

load_dotenv()

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
log_level = logging.DEBUG if ENVIRONMENT == "development" else logging.INFO
logging.basicConfig(level=log_level)
logger = logging.getLogger("agentkit")

proveedor = obtener_proveedor()
PORT = int(os.getenv("PORT", 8000))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa la base de datos al arrancar el servidor."""
    await inicializar_db()
    logger.info("Base de datos inicializada")
    logger.info(f"Servidor corriendo en puerto {PORT}")
    logger.info(f"Proveedor: {proveedor.__class__.__name__}")
    yield


app = FastAPI(
    title="AgentKit — Sutil Pastelería",
    version="2.0.0",
    lifespan=lifespan
)


@app.get("/")
async def health_check():
    """Endpoint de salud."""
    return {"status": "ok", "service": "agentkit"}


@app.get("/webhook")
async def webhook_verificacion(request: Request):
    """Verificación GET del webhook (Meta Cloud API)."""
    resultado = await proveedor.validar_webhook(request)
    if resultado is not None:
        return PlainTextResponse(str(resultado))
    return {"status": "ok"}


@app.post("/webhook")
async def webhook_handler(request: Request):
    """
    Recibe y procesa mensajes de WhatsApp.
    Soporta texto, audios y comandos especiales.
    """
    try:
        mensajes = await proveedor.parsear_webhook(request)

        for msg in mensajes:
            if msg.es_propio or not msg.texto:
                continue

            telefono = msg.telefono
            texto_original = msg.texto

            # Procesar comandos especiales
            if texto_original.startswith("#pausar"):
                pausar_chat(telefono)
                await guardar_mensaje(telefono, "system", "Chat pausado — requiere atención humana")
                logger.info(f"Chat {telefono} pausado")
                continue

            if texto_original.startswith("#reanudar"):
                reanudar_chat(telefono)
                await guardar_mensaje(telefono, "system", "Chat reanudado")
                logger.info(f"Chat {telefono} reanudado")
                continue

            # Si el chat está pausado, no responder automáticamente
            if esta_pausado(telefono):
                logger.info(f"Chat {telefono} pausado — mensaje ignorado")
                continue

            # Transcribir audio si es necesario
            texto = texto_original
            if texto.lower().startswith("audio:") or "ogg" in texto.lower():
                # El proveedor habrá descargado el audio
                ruta_audio = texto.replace("audio:", "").strip()
                texto_transcrito = await transcribir_audio(ruta_audio)
                if texto_transcrito:
                    texto = texto_transcrito
                    logger.info(f"Audio transcrito: {texto}")
                    await guardar_mensaje(telefono, "system", f"[Audio transcrito: {texto}]")

            logger.info(f"Mensaje de {telefono}: {texto}")

            # Consultar Google Sheets para cliente recurrente
            contexto_cliente = None
            cliente_recurrente = await buscar_cliente_recurrente(telefono)
            if cliente_recurrente:
                contexto_cliente = cliente_recurrente

            # Obtener historial
            historial = await obtener_historial(telefono)

            # Inyectar contexto de cliente recurrente en el historial si existe
            if contexto_cliente:
                prefijo = f"[Cliente recurrente: {contexto_cliente['nombre']}, " \
                         f"compra habitualmente: {contexto_cliente['producto_habitual']}, " \
                         f"es VIP: {contexto_cliente['es_vip']}]"
                historial.insert(0, {"role": "system", "content": prefijo})

            # Generar respuesta
            respuesta = await generar_respuesta(texto, historial)

            # Guardar en memoria
            await guardar_mensaje(telefono, "user", texto)
            await guardar_mensaje(telefono, "assistant", respuesta)

            # Enviar respuesta
            await proveedor.enviar_mensaje(telefono, respuesta)

            logger.info(f"Respuesta a {telefono}: {respuesta[:100]}...")

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Error en webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))
