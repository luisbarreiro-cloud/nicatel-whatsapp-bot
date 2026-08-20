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
from datetime import datetime
import anthropic

from sheets_helper import consultar_ventas

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

MODEL = "claude-sonnet-4-6"

TOOLS = [
    {
        "name": "consultar_ventas",
        "description": (
            "Consulta los datos de ventas de Nicatel filtrados por fecha, "
            "producto, categoría o canal, y devuelve totales de unidades "
            "y facturación. Podés agrupar el resultado por producto, "
            "categoria, canal o mes."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "fecha_inicio": {
                    "type": "string",
                    "description": "Fecha desde, formato YYYY-MM-DD. Opcional.",
                },
                "fecha_fin": {
                    "type": "string",
                    "description": "Fecha hasta, formato YYYY-MM-DD. Opcional.",
                },
                "producto": {
                    "type": "string",
                    "description": "Nombre o parte del nombre del producto. Opcional.",
                },
                "categoria": {
                    "type": "string",
                    "description": "Categoría de producto (ej: TV, Celular). Opcional.",
                },
                "canal": {
                    "type": "string",
                    "description": "Canal de venta (ej: Tienda, MercadoLibre, Interior). Opcional.",
                },
                "agrupar_por": {
                    "type": "string",
                    "enum": ["producto", "categoria", "canal", "mes"],
                    "description": "Cómo desglosar el resultado. Opcional.",
                },
            },
        },
    }
]

SYSTEM_PROMPT = f"""Sos el asistente comercial de Nicatel S.A., una distribuidora
uruguaya de electrónica de consumo. Respondés por WhatsApp a Luisao, el
Gerente Comercial, que te va a hacer preguntas en español rioplatense sobre
las ventas de la empresa (unidades vendidas, facturación, por producto,
categoría, canal o período).

Hoy es {datetime.now().strftime('%Y-%m-%d')}.

Usá la herramienta consultar_ventas para traer los datos reales antes de
responder cualquier pregunta sobre números de ventas. Nunca inventes cifras.

Cuando interpretes fechas relativas ("este mes", "el mes pasado", "en lo
que va del año"), convertilas vos a fechas concretas antes de llamar a la
herramienta.

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

    # Loop hasta que Claude devuelva una respuesta final (sin tool_use)
    for _ in range(5):  # límite de seguridad para evitar loops infinitos
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason != "tool_use":
            # Extraer el texto final
            texto = "".join(
                block.text for block in response.content if block.type == "text"
            )
            return texto.strip() or "No pude generar una respuesta, probá reformular la pregunta."

        # Hay uno o más tool_use: los ejecutamos y devolvemos los resultados
        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for block in response.content:
            if block.type == "tool_use" and block.name == "consultar_ventas":
                try:
                    resultado = consultar_ventas(**block.input)
                except Exception as e:
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
