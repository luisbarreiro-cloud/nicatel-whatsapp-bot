"""
claude_helper.py
-----------------
Arma la conversación con Claude: le da la herramienta "consultar_ventas"
para que decida qué filtros aplicar según la pregunta en lenguaje natural,
ejecuta esa consulta contra Google Sheets, y le devuelve el resultado
para que Claude redacte la respuesta final en español, lista para
WhatsApp.
"""

import os
import logging
from datetime import datetime
import anthropic

from sheets_helper import consultar_ventas

logger = logging.getLogger("whatsapp-sales-bot")

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

MODEL = "claude-sonnet-4-6"

TOOLS = [
    {
        "name": "consultar_ventas",
        "description": (
            "Consulta los datos de facturación de Nicatel (Samsung y Nstore) "
            "filtrados por mes, trimestre, producto, categoría, familia, "
            "marca o punto de venta, y devuelve totales de unidades y "
            "facturación en USD. Podés agrupar el resultado por categoría, "
            "familia, marca, punto de venta o mes."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "mes": {
                    "type": "string",
                    "description": (
                        "Nombre del mes en español (Enero, Febrero, Marzo, "
                        "Abril, Mayo, Junio, Julio...). Todos los datos "
                        "cargados hasta ahora son de 2026. Opcional."
                    ),
                },
                "trimestre": {
                    "type": "string",
                    "description": "Q1 o Q2 (trimestres cargados hasta ahora). Opcional.",
                },
                "producto": {
                    "type": "string",
                    "description": "Nombre o parte del nombre del producto, o SKU. Opcional.",
                },
                "categoria": {
                    "type": "string",
                    "description": (
                        "Categoría de producto, ej: TV, Celulares, CONSUMER, "
                        "AIRE, AUDIO, Monitor, Tablet, Wearables, etc. Opcional."
                    ),
                },
                "familia": {
                    "type": "string",
                    "description": "Familia de producto, ej: Neo Qled, Qled, Side by Side, Galaxy A, Buds. Opcional.",
                },
                "marca": {
                    "type": "string",
                    "description": "Marca, ej: Samsung, Xiaomi, JBL, Iphone. Opcional.",
                },
                "punto_venta": {
                    "type": "string",
                    "description": (
                        "Punto de venta: SBS, PDE, WEB, Nuevocentro, Tres cruces, "
                        "Car one. Opcional."
                    ),
                },
                "agrupar_por": {
                    "type": "string",
                    "enum": ["categoria", "familia", "marca", "punto_venta", "mes"],
                    "description": "Cómo desglosar el resultado. Opcional.",
                },
            },
        },
    }
]

SYSTEM_PROMPT = f"""Sos el asistente comercial de Nicatel S.A., una distribuidora
uruguaya de electrónica de consumo (Samsung y Nstore). Respondés por
WhatsApp a Luisao, el Gerente Comercial, que te va a hacer preguntas en
español rioplatense sobre la facturación de la empresa (unidades vendidas,
facturación en USD, por producto, categoría, familia, marca, punto de
venta o período).

Hoy es {datetime.now().strftime('%Y-%m-%d')}.

IMPORTANTE sobre los datos disponibles: la planilla actual tiene datos
mensuales cargados de Enero a Junio de 2026 (Q1 y Q2), y NO tiene columna
de año — asumí siempre 2026 salvo que Luisao diga explícitamente otro año,
en cuyo caso aclarale que esa planilla todavía no tiene datos de ese año.

Usá la herramienta consultar_ventas para traer los datos reales antes de
responder cualquier pregunta sobre números de facturación. Nunca inventes
cifras.

Cuando interpretes períodos relativos ("este mes", "el mes pasado", "en lo
que va del año"), convertilos vos al nombre de mes o trimestre concreto
antes de llamar a la herramienta (recordá que sólo hay datos hasta Junio).

Al responder:
- Sé breve y directo, como un mensaje de WhatsApp (no uses markdown ni
  encabezados, esto se lee en el celular).
- Dale los números concretos primero, después un comentario breve si suma valor.
- Si la consulta no da resultados, decilo claramente y sugerí revisar el
  período o el filtro usado.
"""


def responder_pregunta(pregunta_usuario: str) -> str:
    """Recibe la pregunta en texto plano de WhatsApp y devuelve la
    respuesta final en texto plano, ya lista para reenviar."""

    messages = [{"role": "user", "content": pregunta_usuario}]

    for _ in range(5):
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason != "tool_use":
            texto = "".join(
                block.text for block in response.content if block.type == "text"
            )
            return texto.strip() or "No pude generar una respuesta, probá reformular la pregunta."

        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for block in response.content:
            if block.type == "tool_use" and block.name == "consultar_ventas":
                try:
                    resultado = consultar_ventas(**block.input)
                except Exception as e:
                    logger.exception("Error en consultar_ventas")
                    resultado = {"error": str(e)}

                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(resultado),
                    }
                )

        messages.append({"role": "user", "content": tool_results})

    return "Tuve un problema procesando tu consulta, probá de nuevo en un rato."
