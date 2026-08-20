"""
main.py
-------
Servidor web que recibe los mensajes entrantes de WhatsApp (vía Twilio),
se los pasa a Claude para que consulte los datos de ventas, y devuelve
la respuesta al chat.

Para correrlo localmente (pruebas):
    uvicorn main:app --reload --port 8000

Para desplegarlo, ver README.md.
"""

import os
import logging
from fastapi import FastAPI, Request, Response
from twilio.twiml.messaging_response import MessagingResponse

from claude_helper import responder_pregunta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("whatsapp-sales-bot")

app = FastAPI(title="Nicatel WhatsApp Sales Bot")


@app.get("/")
def health_check():
    return {"status": "ok", "servicio": "Nicatel WhatsApp Sales Bot"}


@app.post("/whatsapp")
async def whatsapp_webhook(request: Request):
    """Twilio llama a este endpoint cada vez que llega un mensaje de WhatsApp."""
    form = await request.form()
    pregunta = form.get("Body", "").strip()
    remitente = form.get("From", "desconocido")

    logger.info(f"Mensaje recibido de {remitente}: {pregunta}")

    resp = MessagingResponse()

    if not pregunta:
        resp.message("No recibí ningún texto en tu mensaje, probá de nuevo.")
        return Response(content=str(resp), media_type="text/xml")

    try:
        respuesta = responder_pregunta(pregunta)
    except Exception as e:
        logger.exception("Error procesando la pregunta")
        respuesta = (
            "Uy, tuve un error procesando tu consulta. "
            f"Detalle técnico: {e}"
        )

    resp.message(respuesta)
    return Response(content=str(resp), media_type="text/xml")
