from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from openai import AsyncOpenAI
from websockets.exceptions import ConnectionClosed

# Importa Uvicorn, un servidor ASGI para ejecutar aplicaciones FastAPI
import uvicorn

# Definición del endpoint donde se encuentra el servicio de la API
ENDPOINT = "http://127.0.0.1:39281/v1"

# Modelo de IA seleccionado para el procesamiento
#MODEL = "phi-3.5:3b-gguf-q4-km"
#MODEL = "deepseek-r1-distill-qwen-14b:14b-gguf-q4-km"
MODEL = "llama3.2:3b-gguf-q4-km"

# Creación del cliente de OpenAI utilizando la API asíncrona
client = AsyncOpenAI(
    base_url=ENDPOINT,
    api_key="not-needed"
)

# Instancia de la aplicación FastAPI
app = FastAPI()

# Monta el directorio de archivos estáticos en la ruta /static
app.mount("/static", StaticFiles(directory="static"), name="static")
 
# Ruta raíz de la aplicación
@app.get("/", response_class=HTMLResponse)
# Redirige la petición a la página de inicio
async def root( request: Request ):
    return RedirectResponse("/static/index.html")

# Ruta de inicialización de la aplicación
@app.websocket("/init")

# Inicializa la conexión WebSocket
async def init( websocket: WebSocket ):
    await websocket.accept()
    
    try:
        # Bucle de recepción de mensajes
        while True:
            data = await websocket.receive_json()
            # Inicia la conversación con el sistema
            await websocket.send_json( { "action": "init_system_response" } )
            # Procesa los mensajes recibidos
            response = await process_messages( data, websocket )
            await websocket.send_json( { "action": "finish_system_response" } )
    except (WebSocketDisconnect, ConnectionClosed):
        print( "Conexión cerrada" )

# Procesa los mensajes recibidos y envía la respuesta al cliente
async def process_messages( messages, websocket ):
    completion_payload = {
        "messages": messages
    }

    # Realiza la petición a la API de OpenAI para obtener la respuesta
    response = await client.chat.completions.create(
        top_p=0.9,
        temperature=0.6,
        model=MODEL,
        messages=completion_payload["messages"],
        stream=True
    )

    respStr = ""
    # Bucle de recepción de mensajes
    async for chunk in response:
        if (not chunk.choices[0] or
            not chunk.choices[0].delta or
            not chunk.choices[0].delta.content):
          continue
          
        await websocket.send_json( { "action": "append_system_response", "content": chunk.choices[0].delta.content } ) # Envía la respuesta al cliente

    return respStr

# Inicia el servidor Uvicorn para ejecutar la aplicación FastAPI
uvicorn.run(app, host="0.0.0.0", port=8000)

