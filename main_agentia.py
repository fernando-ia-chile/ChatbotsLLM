from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from openai import AsyncOpenAI, OpenAI
from websockets.exceptions import ConnectionClosed

import asyncio
import logging

"""
    Ejemplo:
    Código permite a los usuarios interactuar en tiempo real con un chatbot que 
    interpreta sus mensajes, genera y ejecuta consultas SQL sobre una tabla de 
    facturas, y devuelve los resultados de forma interactiva a través de un 
    WebSocket.
"""

# Configuración básica de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)




import duckdb
import uvicorn

# Definición del endpoint donde se encuentra el servicio de la API
# selecciono el de deepseek (pesa (GB))
ENDPOINT = "http://127.0.0.1:39281/v1"
#MODEL = "phi-3.5:3b-gguf-q4-km"
#MODEL = "llama3.2:3b-gguf-q4-km"
MODEL = "deepseek-r1-distill-qwen-14b:14b-gguf-q4-km"

client = AsyncOpenAI(
    base_url=ENDPOINT,
    api_key="not-needed"
)

client2 = OpenAI(
    base_url=ENDPOINT,
    api_key="not-needed"
)

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
 
@app.get("/", response_class=HTMLResponse)
async def root( request: Request ):
    return RedirectResponse("/static/index.html")

@app.websocket("/init")
async def init( websocket: WebSocket ):
    await websocket.accept()
    
    try:
        while True:
            data = await websocket.receive_json()

            await websocket.send_json( { "action": "init_system_response" } )
            response = await plan_messages( data, websocket )
            await websocket.send_json( { "action": "finish_system_response" } )
    except (WebSocketDisconnect, ConnectionClosed):
        print( "Conexión cerrada" )

async def plan_messages( messages, websocket ):
    pmsg = [ 
        { "role": "system", "content": """
        Responde solo 'No' en caso de no ser posible responder con los datos de la tabla.
        Responde solo 'No' en caso de pedir información de empresas que no sean Lostsys.
        Responde solo la sentencia SQL para la base de datos DuckDB a ejecutar en caso de poder obtener los datos de la tabla.
        Responde siempre Sin explicación, Sin notas, Sin delimitaciones.
        Disponemos de una tabla de base de datos llamada 'facturas' que contiene estos campos: 'fecha' del tipo VARCHAR usando el formato de fecha 'YYYY-MM-DD', 'cliente' tipo INTEGER que contiene el id de cliente, 'pais' tipo VARCHAR que contiene 'ES' como España y 'UK' como reino unido, 'importe' con el total de la factura. 
        No puedes suponer nada ni usar otras tablas o datos que no sean los de la tabla 'facturas'.
        Para filtrar por el campo fecha usa siempre 'LIKE', nunca utilices funciones de fecha como YEAR, MONTH, EXTRACT.
        """ },
        { "role": "user", "content": messages[ -1 ]["content"] }         
    ]

    response = client2.chat.completions.create(
        top_p=0.9,
        temperature=0.9,
        model=MODEL,
        messages=pmsg,
    )

    logger.info(f"Respuesta recibida: {r}")

    r = response.choices[0].message.content
    print( r )
    r = clean_sql( r )

    if not r.startswith("No"):
        await websocket.send_json( { "action": "append_system_response", "content": r } )
        await websocket.send_json( { "action": "append_system_response", "content": "\n\n<b>Resultado: </b>" + execute__query( r ) } )

        return

    return await process_messages( messages, websocket )

def execute__query( sql ):
    return str( duckdb.sql( sql ).fetchall() )

def clean_sql( sql ):
    if sql.find("<|end_of_text|>") != -1: sql = sql[sql.find("<|end_of_text|>")+15:]
    if sql.find("</think>") != -1: sql = sql[sql.find("</think>")+8:]

    sql = sql.strip()

    if sql.startswith("```sql"): sql = sql[6:]
    if sql.startswith("```"): sql = sql[3:]
    if sql.endswith("```"): sql = sql[:len(sql)-3]
    if sql.find("```") != -1: sql = sql[sql.find("```"):]
    sql = sql.replace( "FROM facturas", "FROM './facturas.csv'" )
    sql = sql.replace( "fecha", "CAST(fecha AS VARCHAR)" )
    logger.error(f"La query sugerida para el cliente: {sql}")
    return sql


async def process_messages( messages, websocket ):
    completion_payload = {
        "messages": messages
    }
    logger.info("Iniciando stream de respuesta desde client (client.chat.completions.create)")

    response = await client.chat.completions.create(
        top_p=0.9,
        temperature=0.6,
        model=MODEL,
        messages=completion_payload["messages"],
        stream=True
    )

    respStr = ""
    async for chunk in response:
        if (not chunk.choices[0] or
            not chunk.choices[0].delta or
            not chunk.choices[0].delta.content):
          continue

        await websocket.send_json( { "action": "append_system_response", "content": chunk.choices[0].delta.content } )

    return respStr


uvicorn.run(app, host="0.0.0.0", port=8000)
