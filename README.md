# Nicatel WhatsApp Sales Bot

Preguntale a Claude por WhatsApp cosas como *"¿cuántas TV se vendieron en julio?"*
o *"¿cuánto facturamos en MercadoLibre este mes?"* y te contesta con los
datos reales de tu planilla de ventas.

## Cómo funciona (resumen)

```
Vos escribís por WhatsApp
        ↓
Twilio recibe el mensaje y lo manda a tu servidor
        ↓
Tu servidor le pasa la pregunta a Claude, con la herramienta "consultar_ventas"
        ↓
Claude decide qué filtros aplicar → tu servidor los ejecuta contra tu Google Sheet
        ↓
Claude redacta la respuesta final → tu servidor te la reenvía por WhatsApp
```

No hay nada corriendo 24/7 en tu computadora: el servidor vive en un
hosting gratuito (Render), así que funciona aunque tengas la PC apagada.

---

## Paso 1 — Preparar tu Google Sheet de ventas

1. Armá (o migrá tu Excel actual a) una planilla de Google Sheets con
   estas columnas exactas en la primera fila:

   | Fecha | Producto | Categoria | Cantidad | PrecioUnitario | Canal |
   |-------|----------|-----------|----------|----------------|-------|
   | 2026-08-10 | TV Samsung 55 QLED | TV | 3 | 45000 | Tienda |

   Te dejé un ejemplo armado en `sample_data/ventas_ejemplo.xlsx` — abrilo,
   copiá el contenido a un Google Sheet nuevo, y después reemplazá los
   datos de ejemplo por los tuyos reales.

2. Compartila: botón **Compartir** (arriba a la derecha) → cambiar a
   **"Cualquier persona con el enlace" → rol "Lector"**. Esto no la hace
   pública en buscadores, sólo accesible para quien tenga el link exacto.

3. Copiá el ID de la planilla desde la URL:
   ```
   https://docs.google.com/spreadsheets/d/ESTE-ES-EL-ID/edit#gid=0
                                              ^^^^^^^^^^^^         ^
                                              GOOGLE_SHEET_ID   GOOGLE_SHEET_GID
   ```

---

## Paso 2 — Crear tu API key de Claude

1. Andá a [console.anthropic.com](https://console.anthropic.com) → API Keys
   → **Create Key**.
2. Guardala, la vas a necesitar en el Paso 4. (Este proyecto consume la
   API de pago por uso — con el volumen de "una persona preguntando
   varias veces por día" el costo es de centavos de dólar al mes).

---

## Paso 3 — Crear tu cuenta de Twilio y activar el Sandbox de WhatsApp

1. Registrate gratis en [twilio.com/try-twilio](https://www.twilio.com/try-twilio).
2. En el panel, buscá **Messaging → Try it out → Send a WhatsApp message**.
   Ahí te va a dar:
   - Un número de WhatsApp de Twilio (algo como `+1 415 523 8886`)
   - Un código tipo `join palabra-clave`
3. Desde tu WhatsApp personal, mandale un mensaje a ese número con el
   texto `join palabra-clave` que te dieron. Así tu WhatsApp queda
   conectado al sandbox (esto es gratis, pero hay que "reactivarlo" cada
   72hs si no se usa — para uso diario tuyo no vas a notar esto. Cuando
   quieras algo permanente y con tu propio número, se pide un WhatsApp
   Sender de Twilio, que ya no tiene ese límite).

*(Nota: no hace falta que copies el Account SID/Auth Token para esta
primera versión — sólo se usan si más adelante querés mandar mensajes
salientes vos, no como respuesta a un mensaje entrante.)*

---

## Paso 4 — Desplegar el servidor en Render (gratis)

1. Subí esta carpeta a un repositorio de GitHub (podés crear uno nuevo
   y arrastrar estos archivos vía la web de GitHub, sin usar la terminal).
2. Andá a [render.com](https://render.com) → **New → Web Service** →
   conectá tu repo de GitHub.
3. Configurá:
   - **Build command**: `pip install -r requirements.txt`
   - **Start command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. En **Environment Variables**, cargá:
   - `ANTHROPIC_API_KEY` → tu key del Paso 2
   - `GOOGLE_SHEET_ID` → el ID del Paso 1
   - `GOOGLE_SHEET_GID` → el gid del Paso 1 (normalmente `0`)
5. Deploy. Cuando termine, Render te da una URL tipo
   `https://nicatel-sales-bot.onrender.com`.

*(Nota: el plan gratis de Render "duerme" el servicio si no se usa por
un rato, y tarda ~30 segundos en "despertar" con el primer mensaje del
día. Si eso te molesta, el plan pago arranca en USD 7/mes y queda siempre
activo.)*

---

## Paso 5 — Conectar Twilio con tu servidor

1. Volvé al panel de Twilio, sección del Sandbox de WhatsApp.
2. En **"When a message comes in"**, pegá:
   ```
   https://nicatel-sales-bot.onrender.com/whatsapp
   ```
   (con tu URL real de Render) y método `HTTP POST`.
3. Guardar.

¡Listo! Ahora mandale un WhatsApp al número del sandbox de Twilio
preguntando algo como:

> ¿Cuántas TV se vendieron en julio?

> ¿Cuánto facturamos en MercadoLibre este mes?

> Dame el desglose de ventas por categoría del último mes

---

## Cómo actualizar los datos

Simplemente editá el Google Sheet (agregando filas nuevas de ventas) —
el bot lee la planilla en vivo en cada consulta, no hay que reiniciar
nada.

## Próximos pasos posibles (cuando quieras escalar esto)

- Conectar varias pestañas/planillas (Import TV, Open Tiendas, etc.) y
  que Claude elija cuál consultar según la pregunta.
- Sumar más usuarios del equipo (Marianella, Joaquín) con permisos
  distintos.
- Pasar de Google Sheets a una base de datos real si el volumen de datos
  crece mucho.
  
- Agregar gráficos: que el bot te mande una imagen de un gráfico simple
  en vez de sólo texto.

Cualquiera de estos, avisame y lo desarrollamos.
