from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from openai import AsyncOpenAI
from websockets.exceptions import ConnectionClosed

import chromadb
import json
import uvicorn

"""
      Es un asistente virtual para la empresa Lostsys. El asistente está diseñado para 
      ayudar a los clientes a encontrar servicios o productos ofrecidos por la empresa
"""

ENDPOINT = "http://127.0.0.1:39281/v1"
#MODEL = "phi-3.5:3b-gguf-q4-km"
#MODEL = "deepseek-r1-distill-qwen-14b:14b-gguf-q4-km"
MODEL = "llama3.2:3b-gguf-q4-km"

client = chromadb.Client()

collection = client.create_collection("all-my-documents")

collection.add(
    documents=[
        "La empresa Fhirsaludnet se dedica a ofrecer servícios y asesoría a empresas sobre informática corporativa como software de gestión, CRMs, ERPs, portales corporativos, eCommerce, formación, DevOps, etc.",
        "En Fhirsaludnet podemos ayudarte ha mejorar tus procesos de CI/CD con nuestros productos y servícios de DevOps.",
        "En Fhirsaludnet podemos ayudarte a digitalizarte con nuestros servícios de desarrollo de aplicaciones corporativas.",
        "En Fhirsaludnet te podemos entrenar y formar a múltiples áreas de la informática corporativa como desarrollo, Data, IA o DevOps.",
        "En Fhirsaludnet te podemos desarrollar una tienda online para vender por todo el mundo y mas allà.",
        "En Fhirsaludnet te podemos asesorar en interoperabilidad en HL7 FHIR para mejorar la comunicación en la salud por todo el mundo y mas allà",
    ],
    ids=["id1", "id2","id3", "id4","id5", "id6"]
)

system_prompt = """
Eres un asistente de la empresa Fhirsaludnet que ayuda a sus clientes a encontrar el servicio o producto que les interesa. Sigue estas instrucciones:
- Ofrece respuestas cortas y concisas de no mas de 25 palabras. 
- No ofrezcas consejos, productos o servícios de terceros.
- Explica al cliente cosas relacionadas con en la siguiente lista JSON: """


client = AsyncOpenAI(
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
            response = await process_messages( data, websocket )
            await websocket.send_json( { "action": "finish_system_response" } )
    except (WebSocketDisconnect, ConnectionClosed):
        print( "Conexión cerrada" )

async def process_messages( messages, websocket ):

    results = collection.query(
        query_texts=[ messages[ -1 ]["content"] ], 
        n_results=2 
    )

    pmsg = [ { "role": "system", "content": system_prompt + str( results["documents"][0] ) } ]
    print( json.dumps( pmsg + messages, indent=4) )
    completion_payload = {
        "messages": pmsg + messages
    }

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

