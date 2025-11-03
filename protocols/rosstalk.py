# /protocols/rosstalk.py
# by Arnaud Cresp – 2025

import asyncio
from services.patch_bus import emit_patch
from services.logical import load_logical_ids
from services.cache import read_cache

class RossTalkEmulator:
    def __init__(self, host="0.0.0.0", port=7788):
        self.host = host
        self.port = port
        self.server = None
        self.clients = set()
        self.routing = {}
        self.inputs = {}
        self.outputs = {}

    def load_labels(self):
        logicals = load_logical_ids()
        sources = logicals.get("sources", {})
        receivers = logicals.get("receivers", {})

        self.inputs = {
            int(v["id"]): k for k, v in sources.items()
            if "id" in v and isinstance(v["id"], int)
        }
        self.outputs = {
            int(v["id"]): k for k, v in receivers.items()
            if "id" in v and isinstance(v["id"], int)
        }

    async def start(self):
        self.load_labels()
        await self.refresh_routing_from_nmos()

        self.server = await asyncio.start_server(
            self.handle_client, self.host, self.port
        )
        print(f"[ROSS PROTOCOL] RossTalk emulator running on {self.host}:{self.port}")
        await self.server.serve_forever()

    async def stop(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            print("[ROSS PROTOCOL] RossTalk emulator stopped")

    async def handle_client(self, reader, writer):
        addr = writer.get_extra_info("peername")
        print(f"[ROSS PROTOCOL] New connection from {addr}")
        self.clients.add(writer)

        try:
            while not reader.at_eof():
                line = await reader.readline()
                if not line:
                    break
                line = line.decode().strip()
                await self.process_line(line)
        except Exception as e:
            print(f"[ROSS PROTOCOL] Client error: {e}")
        finally:
            self.clients.discard(writer)
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def process_line(self, line):
        try:
            if line.upper().startswith("XPT"):
                tokens = line.split()
                d = s = None
                for token in tokens:
                    if token.upper().startswith("D:"):
                        try:
                            d = int(token[2:])
                        except:
                            continue
                    elif token.upper().startswith("S:"):
                        try:
                            s = int(token[2:])
                        except:
                            continue
                if d is not None and s is not None:
                    if d in self.outputs and s in self.inputs:
                        await emit_patch(s, d, origin="RossTalk")
                        self.routing[d] = s
                        print(f"[ROSS PROTOCOL] Patched output {d} ← input {s}")
        except Exception as e:
            print(f"[ROSS PROTOCOL] Error processing line: {e}")

    async def refresh_routing_from_nmos(self):
        try:
            from services.cache import wait_cache_ready
            await asyncio.to_thread(wait_cache_ready, 30)
            cache = read_cache()

            logicals = load_logical_ids()
            receivers_cache = cache.get("receivers", [])

            for receiver_name, receiver_info in logicals.get("receivers", {}).items():
                receiver_id = receiver_info.get("id")
                for source_name, source_info in logicals.get("sources", {}).items():
                    match = True
                    for essence in ["video", "audio", "data"]:
                        s_id = source_info.get(essence)
                        r_id = receiver_info.get(essence)
                        if not s_id or not r_id:
                            continue
                        r_obj = next(
                            (r for r in receivers_cache if r.get("id") == r_id), None
                        )
                        if not r_obj or r_obj.get("subscription", {}).get("sender_id") != s_id:
                            match = False
                            break
                    if match:
                        self.routing[receiver_id] = source_info.get("id")
                        break
        except Exception as e:
            print(f"[ROSS PROTOCOL] Failed to sync routing from NMOS: {e}")

    async def set_routing(self, sender_id, receiver_id, origin="external", force_broadcast=False):
        current = self.routing.get(receiver_id)
        if current == sender_id and not force_broadcast:
            return
        self.routing[receiver_id] = sender_id
        print(f"[ROSS PROTOCOL] Update from {origin}: {receiver_id} ← {sender_id} (was {current})")

    async def reload_and_broadcast(self):
        self.load_labels()
        await self.refresh_routing_from_nmos()
        print("[ROSS PROTOCOL] Reloaded logical labels and updated routing.")