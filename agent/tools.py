# agent/tools.py — Herramientas avanzadas para Sutil Pastelería
"""
Integración con Google Sheets, Calendar, Gmail y OpenAI Whisper.
Gestión de clientes, pedidos, entregas y notificaciones.
"""

import os
import yaml
import logging
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv
from typing import Optional

# Google APIs
from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
from google.oauth2.credentials import Credentials as UserCredentials
from googleapiclient.discovery import build
import base64
from email.mime.text import MIMEText

load_dotenv()
logger = logging.getLogger("agentkit")

# ════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ════════════════════════════════════════════════════════════

def cargar_info_negocio() -> dict:
    """Carga la información del negocio desde business.yaml."""
    try:
        with open("config/business.yaml", "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.error("config/business.yaml no encontrado")
        return {}


# Catálogo de productos con precios
CATALOGO = {
    "pan_hamburguesa": {
        "nombre": "pan de hamburguesa",
        "variedades": ["Clásico", "Integral", "Brioche", "Ajonjolí", "Carbón Activo"],
        "precios": {"unidad": 800, "paquete_6": 4500, "paquete_12": 8500, "mayor_50": 700}
    },
    "pan_perro": {
        "nombre": "pan para perro (hotdog)",
        "precios": {"unidad": 700, "paquete_6": 3900, "paquete_12": 7500, "mayor_50": 600}
    },
    "pan_sandwich": {
        "nombre": "pan sándwich",
        "precios": {"unidad": 750, "paquete_6": 4200, "paquete_12": 8000, "mayor_50": 650}
    }
}

# ════════════════════════════════════════════════════════════
# GOOGLE SHEETS — CRM y PEDIDOS
# ════════════════════════════════════════════════════════════

def obtener_sheets_service():
    """Retorna cliente autenticado de Google Sheets."""
    try:
        creds_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "credentials.json")
        if not os.path.exists(creds_path):
            logger.warning(f"No encontrado {creds_path} — Google Sheets deshabilitado")
            return None

        creds = Credentials.from_service_account_file(
            creds_path,
            scopes=['https://www.googleapis.com/auth/spreadsheets',
                    'https://www.googleapis.com/auth/calendar',
                    'https://www.googleapis.com/auth/gmail.send']
        )
        return build('sheets', 'v4', credentials=creds)
    except Exception as e:
        logger.error(f"Error autenticación Google Sheets: {e}")
        return None


async def buscar_cliente_recurrente(telefono: str) -> dict | None:
    """
    Busca el cliente en Google Sheets (Clientes Recurrentes).
    Retorna {nombre, producto_habitual, cantidad_habitual, es_vip} o None.
    """
    sheets = obtener_sheets_service()
    if not sheets:
        return None

    try:
        spreadsheet_id = os.getenv("GOOGLE_SHEET_ID")
        if not spreadsheet_id:
            return None

        # Hoja "Clientes Recurrentes": Nombre | Teléfono | Producto | Cantidad | VIP
        resultado = sheets.values().get(
            spreadsheetId=spreadsheet_id,
            range="'Clientes Recurrentes'!A:E"
        ).execute()

        valores = resultado.get('values', [])[1:]  # Saltar encabezado
        for fila in valores:
            if len(fila) >= 2 and fila[1] == telefono:
                return {
                    "nombre": fila[0],
                    "producto_habitual": fila[2] if len(fila) > 2 else None,
                    "cantidad_habitual": int(fila[3]) if len(fila) > 3 else 0,
                    "es_vip": fila[4].lower() == "sí" if len(fila) > 4 else False
                }
        return None
    except Exception as e:
        logger.error(f"Error buscando cliente recurrente: {e}")
        return None


async def registrar_pedido_sheets(pedido: dict) -> bool:
    """
    Registra un pedido confirmado en Google Sheets (hoja Pedidos).
    Columnas: Fecha | Nombre | Teléfono | Producto | Tipo | Cantidad | Precio |
              Fecha Entrega | Estado | Última Notificación
    """
    sheets = obtener_sheets_service()
    if not sheets:
        return False

    try:
        spreadsheet_id = os.getenv("GOOGLE_SHEET_ID")
        if not spreadsheet_id:
            return False

        fila = [
            datetime.now().isoformat(),
            pedido.get("nombre_cliente", ""),
            pedido.get("telefono", ""),
            pedido.get("producto", ""),
            pedido.get("tipo", ""),
            pedido.get("cantidad", 0),
            pedido.get("precio_total", 0),
            pedido.get("fecha_entrega", ""),
            "Recibido",
            datetime.now().isoformat()
        ]

        sheets.values().append(
            spreadsheetId=spreadsheet_id,
            range="'Pedidos'!A:J",
            valueInputOption="USER_ENTERED",
            body={"values": [fila]}
        ).execute()

        logger.info(f"Pedido registrado en Sheets: {pedido.get('telefono')}")
        return True
    except Exception as e:
        logger.error(f"Error registrando pedido en Sheets: {e}")
        return False


# ════════════════════════════════════════════════════════════
# GOOGLE CALENDAR — ENTREGAS
# ════════════════════════════════════════════════════════════

def obtener_calendar_service():
    """Retorna cliente autenticado de Google Calendar."""
    try:
        creds_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "credentials.json")
        if not os.path.exists(creds_path):
            return None

        creds = Credentials.from_service_account_file(
            creds_path,
            scopes=['https://www.googleapis.com/auth/calendar']
        )
        return build('calendar', 'v3', credentials=creds)
    except Exception as e:
        logger.error(f"Error autenticación Google Calendar: {e}")
        return None


async def crear_evento_entrega(pedido: dict) -> bool:
    """
    Crea evento en Google Calendar para la entrega.
    Título: 'Entrega: [cantidad] [producto] [tipo] - [nombre cliente]'
    """
    calendar = obtener_calendar_service()
    if not calendar:
        return False

    try:
        fecha_entrega = pedido.get("fecha_entrega", "")
        if not fecha_entrega:
            return False

        titulo = f"Entrega: {pedido.get('cantidad', '')} {pedido.get('producto', '')} " \
                 f"{pedido.get('tipo', '')} - {pedido.get('nombre_cliente', '')}"

        evento = {
            'summary': titulo,
            'description': f"Teléfono: {pedido.get('telefono', '')}\n"
                          f"Cantidad: {pedido.get('cantidad', '')}\n"
                          f"Precio: ${pedido.get('precio_total', '')}",
            'start': {'date': fecha_entrega},
            'end': {'date': (datetime.fromisoformat(fecha_entrega) + timedelta(days=1)).date().isoformat()},
        }

        calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "primary")
        calendar.events().insert(calendarId=calendar_id, body=evento).execute()

        logger.info(f"Evento creado en Calendar: {titulo}")
        return True
    except Exception as e:
        logger.error(f"Error creando evento Calendar: {e}")
        return False


# ════════════════════════════════════════════════════════════
# GMAIL — NOTIFICACIONES A PRODUCCIÓN
# ════════════════════════════════════════════════════════════

def obtener_gmail_service():
    """Retorna cliente autenticado de Gmail."""
    try:
        creds_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "credentials.json")
        if not os.path.exists(creds_path):
            return None

        creds = Credentials.from_service_account_file(
            creds_path,
            scopes=['https://www.googleapis.com/auth/gmail.send']
        )
        return build('gmail', 'v1', credentials=creds)
    except Exception as e:
        logger.error(f"Error autenticación Gmail: {e}")
        return None


async def enviar_notificacion_pedido(pedido: dict) -> bool:
    """
    Envía correo a equipo de producción cuando se confirma un pedido.
    """
    gmail = obtener_gmail_service()
    if not gmail:
        return False

    try:
        info = cargar_info_negocio()
        email_destino = info.get("negocio", {}).get("email_produccion", "")
        if not email_destino:
            logger.warning("email_produccion no configurado en business.yaml")
            return False

        cantidad = pedido.get("cantidad", 0)
        es_pedido_grande = cantidad >= 100

        asunto = f"PEDIDO GRANDE — requiere confirmación de fecha — {pedido.get('nombre_cliente', '')}" \
                if es_pedido_grande else \
                f"Nuevo pedido — {pedido.get('nombre_cliente', '')} — {pedido.get('fecha_entrega', '')}"

        cuerpo = f"""
Nuevo pedido recibido:

Nombre cliente: {pedido.get('nombre_cliente', '')}
Teléfono: {pedido.get('telefono', '')}
Producto: {pedido.get('producto', '')}
Tipo: {pedido.get('tipo', '')}
Cantidad: {pedido.get('cantidad', '')}
Precio total: ${pedido.get('precio_total', '')}
Fecha estimada entrega: {pedido.get('fecha_entrega', '')}
Hora recepción: {datetime.now().isoformat()}
Estado: Recibido
"""

        mensaje = MIMEText(cuerpo)
        mensaje['to'] = email_destino
        mensaje['subject'] = asunto

        raw = base64.urlsafe_b64encode(mensaje.as_bytes()).decode()
        gmail.users().messages().send(userId='me', body={'raw': raw}).execute()

        logger.info(f"Correo enviado a producción: {asunto}")
        return True
    except Exception as e:
        logger.error(f"Error enviando correo: {e}")
        return False


# ════════════════════════════════════════════════════════════
# OPENAI WHISPER — TRANSCRIPCIÓN DE AUDIOS
# ════════════════════════════════════════════════════════════

async def transcribir_audio(ruta_audio: str) -> str | None:
    """
    Transcribe un archivo de audio usando OpenAI Whisper.
    """
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY no configurada")
            return None

        if not os.path.exists(ruta_audio):
            logger.error(f"Archivo de audio no encontrado: {ruta_audio}")
            return None

        # Usar cliente de OpenAI
        from openai import OpenAI
        cliente = OpenAI(api_key=api_key)

        with open(ruta_audio, "rb") as f:
            respuesta = cliente.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                language="es"
            )

        texto = respuesta.text
        logger.info(f"Audio transcrito: {texto[:100]}...")
        return texto
    except Exception as e:
        logger.error(f"Error transcribiendo audio: {e}")
        return None


# ════════════════════════════════════════════════════════════
# CÁLCULO DE PRECIOS
# ════════════════════════════════════════════════════════════

def calcular_precio(producto_key: str, cantidad: int) -> tuple[int, str]:
    """
    Calcula el precio total según la cantidad y presentación.
    Retorna (precio_total, presentacion).
    """
    if producto_key not in CATALOGO:
        return 0, "desconocido"

    precios = CATALOGO[producto_key]["precios"]

    if cantidad >= 50:
        return cantidad * precios["mayor_50"], f"{cantidad} unidades"
    elif cantidad == 12:
        return precios["paquete_12"], "paquete x12"
    elif cantidad == 6:
        return precios["paquete_6"], "paquete x6"
    else:
        return cantidad * precios["unidad"], f"{cantidad} unidad(es)"


# ════════════════════════════════════════════════════════════
# CARRITOS DE COMPRA (en memoria, para sesión actual)
# ════════════════════════════════════════════════════════════

_carritos: dict[str, list[dict]] = {}
_chats_pausados: set[str] = set()


def agregar_al_carrito(telefono: str, producto: str, cantidad: int, tipo: str = "") -> dict:
    """Agrega producto al carrito del cliente."""
    item = {"producto": producto, "cantidad": cantidad, "tipo": tipo}
    _carritos.setdefault(telefono, []).append(item)
    logger.info(f"Carrito {telefono}: {cantidad} x {producto}")
    return {"carrito": _carritos[telefono]}


def ver_carrito(telefono: str) -> list[dict]:
    """Retorna el carrito actual del cliente."""
    return _carritos.get(telefono, [])


def vaciar_carrito(telefono: str) -> None:
    """Vacía el carrito del cliente."""
    _carritos.pop(telefono, None)


async def confirmar_pedido(telefono: str, nombre_cliente: str = "") -> dict:
    """Confirma y registra pedido en Sheets y Calendar."""
    items = _carritos.get(telefono, [])
    if not items:
        return {"ok": False, "mensaje": "El carrito está vacío"}

    # Construir resumen de pedido
    pedido = {
        "telefono": telefono,
        "nombre_cliente": nombre_cliente or "Cliente",
        "items": items,
        "fecha_pedido": datetime.now().isoformat(),
        "fecha_entrega": (datetime.now() + timedelta(days=2)).date().isoformat()
    }

    # Calcular precio total
    precio_total = 0
    for item in items:
        # Encontrar producto en catálogo
        producto_key = next((k for k, v in CATALOGO.items()
                           if v["nombre"].lower() in item["producto"].lower()), None)
        if producto_key:
            precio, _ = calcular_precio(producto_key, item["cantidad"])
            precio_total += precio

    pedido["precio_total"] = precio_total
    pedido["producto"] = items[0].get("producto", "")
    pedido["tipo"] = items[0].get("tipo", "")
    pedido["cantidad"] = sum(i.get("cantidad", 0) for i in items)

    # Registrar en Google Sheets
    await registrar_pedido_sheets(pedido)

    # Crear evento en Calendar
    await crear_evento_entrega(pedido)

    # Enviar notificación a producción
    await enviar_notificacion_pedido(pedido)

    vaciar_carrito(telefono)

    return {"ok": True, "pedido": pedido}


# ════════════════════════════════════════════════════════════
# GESTIÓN DE CHAT PAUSADO/REANUDADO
# ════════════════════════════════════════════════════════════

def pausar_chat(telefono: str) -> None:
    """Pausa atención automática en este chat (para que lo atienda un humano)."""
    _chats_pausados.add(telefono)
    logger.info(f"Chat {telefono} pausado — requiere atención humana")


def reanudar_chat(telefono: str) -> None:
    """Reanuda atención automática en este chat."""
    _chats_pausados.discard(telefono)
    logger.info(f"Chat {telefono} reanudado")


def esta_pausado(telefono: str) -> bool:
    """Verifica si un chat está pausado."""
    return telefono in _chats_pausados
