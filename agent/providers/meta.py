# agent/providers/meta.py — Adaptador para Meta WhatsApp Cloud API
# Generado por AgentKit (Corregido)

import os
import logging
import httpx
from fastapi import Request
from agent.providers.base import ProveedorWhatsApp, MensajeEntrante

logger = logging.getLogger("agentkit")


class ProveedorMeta(ProveedorWhatsApp):
    """Proveedor de WhatsApp usando la API oficial de Meta (Cloud API)."""

    def __init__(self):
        self.whatsapp_token = os.getenv("WHATSAPP_TOKEN")
        self.phone_number_id = os.getenv("PHONE_NUMBER_ID")
        self.webhook_verify_token = os.getenv("WEBHOOK_VERIFY_TOKEN", "agentkit-verify")
        self.api_version = "v21.0"

    async def validar_webhook(self, request: Request) -> dict | int | None:
        """
        Meta requiere verificación GET con hub.verify_token.
        Retorna el challenge como string plano.
        """
        params = request.query_params
        mode = params.get("hub.mode")
        token = params.get("hub.verify_token")
        challenge = params.get("hub.challenge")

        if mode == "subscribe" and token == self.webhook_verify_token:
            logger.info("Webhook verificado por Meta")
            return int(challenge)

        logger.warning(f"Intento de verificación fallido: mode={mode}, token={token}")
        return None

    async def parsear_webhook(self, request: Request) -> list[MensajeEntrante]:
        """
        Parsea el payload JSON de Meta Cloud API diferenciando mensajes de estados.
        """
        try:
            body = await request.json()
        except Exception as e:
            logger.error(f"Error al parsear JSON de Meta: {e}")
            return []

        mensajes = []

        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})

                # Ignorar statuses pero NO hacer continue — seguir procesando messages
                if "statuses" in value:
                    logger.info("Log Meta: Notificación de estado (sent/delivered/read). Ignorando statuses.")

                # Procesar mensajes entrantes siempre que existan, independiente de statuses
                if "messages" in value:
                    for msg in value.get("messages", []):
                        telefono = msg.get("from", "")
                        mensaje_id = msg.get("id", "")
                        tipo_msg = msg.get("type")
                        texto = ""

                        # Si el cliente envió texto
                        if tipo_msg == "text":
                            texto = msg.get("text", {}).get("body", "")

                        # Si el cliente envió un audio
                        elif tipo_msg == "audio":
                            audio_id = msg.get("audio", {}).get("id", "")
                            texto = f"audio:{audio_id}"
                            logger.info(f"Log Meta: Audio detectado. ID de media: {audio_id}")

                        if telefono and texto:
                            mensajes.append(MensajeEntrante(
                                telefono=telefono,
                                texto=texto,
                                mensaje_id=mensaje_id,
                                es_propio=False,
                            ))
                            logger.info(f"Mensaje entrante capturado: {telefono} -> '{texto[:40]}'")

        return mensajes

    async def enviar_mensaje(self, telefono: str, mensaje: str) -> bool:
        """
        Envía mensaje via Meta WhatsApp Cloud API.
        """
        if not self.whatsapp_token or not self.phone_number_id:
            logger.warning(
                f"Variables Meta no configuradas: "
                f"WHATSAPP_TOKEN={bool(self.whatsapp_token)}, "
                f"PHONE_NUMBER_ID={bool(self.phone_number_id)}"
            )
            return False

        url = f"https://graph.facebook.com/{self.api_version}/{self.phone_number_id}/messages"

        headers = {
            "Authorization": f"Bearer {self.whatsapp_token}",
            "Content-Type": "application/json",
        }

        payload = {
            "messaging_product": "whatsapp",
            "to": telefono,
            "type": "text",
            "text": {"body": mensaje},
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.post(url, json=payload, headers=headers)

                if r.status_code == 200:
                    logger.info(f"Respuesta enviada con exito a {telefono} via Meta API")
                    return True
                else:
                    logger.error(
                        f"Error en Meta API ({r.status_code}): {r.text}"
                    )
                    return False

        except httpx.TimeoutException:
            logger.error(f"Timeout al enviar mensaje a {telefono}")
            return False
        except Exception as e:
            logger.error(f"Error al enviar mensaje a {telefono}: {e}")
            return False