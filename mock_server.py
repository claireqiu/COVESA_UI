import asyncio
import websockets
import json
import datetime
from aiohttp import web

connected_clients = set()
rule_updated_event = asyncio.Event()

# Helper: format message
def create_inference_message(tag):
    return json.dumps({
        "type": "data",
        "path": "AI.Reasoner.InferenceResults",
        "instance": "VIN123",
        "schema": "Vehicle",
        "data": json.dumps({
            "HMIEvent.Event": f"AggSituation_{tag}",
            "HMIEvent.Value": "Italian" if tag == "before" else "Spanish"
        }),
        "metadata": {
            "": {
                "timestamps": {
                    "received": {
                        "seconds": int(datetime.datetime.now().timestamp()),
                        "nanos": 123456789
                    }
                }
            }
        }
    })

# WebSocket connection handler
async def ws_handler(websocket, path):
    print("✅ WebSocket client connected")
    connected_clients.add(websocket)
    try:
        async for message in websocket:
            msg = json.loads(message)
            if msg.get("type") == "subscribe":
                await websocket.send(create_inference_message("before"))
                print("📤 Sent BEFORE update message")

                await rule_updated_event.wait()
                await websocket.send(create_inference_message("after"))
                print("📤 Sent AFTER update message")
    except:
        pass
    finally:
        connected_clients.remove(websocket)

# HTTP rule update handler
async def handle_rule_update(request):
    body = await request.text()
    print("🛠️ Rule received")
    rule_updated_event.set()
    return web.Response(text="✅ Rule update received")

# Startup both servers
async def main():
    app = web.Application()
    app.router.add_put("/datastores/dks/content", handle_rule_update)

    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "localhost", 12110).start()

    await websockets.serve(ws_handler, "localhost", 8765)
    print("✅ Mock WebSocket + HTTP server running")
    await asyncio.Future()  # keep running

if __name__ == "__main__":
    asyncio.run(main())
