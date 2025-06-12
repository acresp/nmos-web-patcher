# /protocols/bmdvideohub.py
# by Arnaud Cresp - 2025

import asyncio
from __version__ import __version__
from services.logical import load_logical_ids
from services.cache import refresh_discovery, read_cache
from services.patch_bus import emit_patch

class VideohubEmulator:
    def __init__(self, host='0.0.0.0', port=9990):
        self.host = host
        self.port = port
        self.inputs = {}
        self.outputs = {}
        self.routing = {}
        self.server = None
        self.clients = set()
        self.input_index_map = []
        self.output_index_map = []
        self.input_id_to_index = {}
        self.output_id_to_index = {}
        self._running_task = None
        self.load_labels()

    def load_labels(self):
        logicals = load_logical_ids()
        sources = logicals.get("sources", {})
        receivers = logicals.get("receivers", {})

        self.inputs = {v["id"]: k for k, v in sources.items() if "id" in v and k}
        self.outputs = {v["id"]: k for k, v in receivers.items() if "id" in v and k}
        self.input_index_map = sorted(self.inputs.keys())
        self.output_index_map = sorted(self.outputs.keys())

        self.input_id_to_index = {sid: idx for idx, sid in enumerate(self.input_index_map)}
        self.output_id_to_index = {rid: idx for idx, rid in enumerate(self.output_index_map)}

        self.routing = {}

    async def start(self):
        await self.refresh_routing_from_nmos()
        await self.broadcast_routing_update()

        self.server = await asyncio.start_server(self.handle_client, self.host, self.port)
        print(f"[BMD PROTOCOL] Videohub emulator running on {self.host}:{self.port}")
        self._running_task = asyncio.create_task(self.server.serve_forever())
        await self._running_task

    async def stop(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            print("[BMD PROTOCOL] Emulator stopped.")

        for client in list(self.clients):
            try:
                client.close()
                await client.wait_closed()
            except Exception as e:
                print(f"[BMD PROTOCOL] Failed to close client: {e}")
        self.clients.clear()

        if self._running_task:
            self._running_task.cancel()
            try:
                await self._running_task
            except asyncio.CancelledError:
                pass
            self._running_task = None

    async def handle_client(self, reader, writer):
        addr = writer.get_extra_info('peername')
        print(f"[BMD PROTOCOL] === New session from {addr} ===")
        self.clients.add(writer)

        try:
            self.send(writer, self.preamble())
            self.send(writer, self.device_info())
            self.send(writer, self.input_labels())
            self.send(writer, self.output_labels())
            self.send(writer, self.output_routing())
            await writer.drain()
        except (ConnectionResetError, BrokenPipeError) as e:
            print(f"[BMD PROTOCOL] Client disconnected prematurely: {e}")
            return

        await self.broadcast_routing_update()

        buffer = []
        try:
            while not reader.at_eof():
                line = await reader.readline()
                if not line:
                    break
                line = line.decode().strip()
                print(f"[BMD PROTOCOL] << {line}")
                if not line:
                    await self.process_block(buffer, writer)
                    buffer = []
                else:
                    buffer.append(line)
        finally:
            self.clients.discard(writer)
            try:
                writer.close()
                await writer.wait_closed()
            except Exception as e:
                print(f"[BMD PROTOCOL] Writer cleanup error: {e}")

    def send(self, writer, content: str):
        for line in content.strip().splitlines():
            print(f"[BMD PROTOCOL] >> {line}")
        try:
            writer.write(content.encode() + b"\n\n")
        except Exception as e:
            print(f"[BMD PROTOCOL] Send failed: {e}")

    def preamble(self):
        return "PROTOCOL PREAMBLE:\nVersion: 2.3"

    def device_info(self):
        return (
            "VIDEOHUB DEVICE:\n"
            "Device present: true\n"
            "Model name: NMOS Web Patcher\n"
            f"Video inputs: {len(self.input_index_map)}\n"
            "Video processing units: 0\n"
            f"Video outputs: {len(self.output_index_map)}\n"
            "Video monitoring outputs: 0\n"
            "Serial ports: 0"
        )

    def input_labels(self):
        lines = [f"{i} {self.inputs[logical_id]}" for i, logical_id in enumerate(self.input_index_map)]
        return "INPUT LABELS:\n" + "\n".join(lines)

    def output_labels(self):
        lines = [f"{i} {self.outputs[logical_id]}" for i, logical_id in enumerate(self.output_index_map)]
        return "OUTPUT LABELS:\n" + "\n".join(lines)

    def output_routing(self):
        lines = []
        for i, output_id in enumerate(self.output_index_map):
            sender_id = self.routing.get(output_id)
            input_idx = self.input_id_to_index.get(sender_id)
            if sender_id is not None and input_idx is not None:
                lines.append(f"{i} {input_idx}")
            else:
                print(f"[BMD PROTOCOL] No valid route for output {i} ({self.outputs.get(output_id)})")
        return "VIDEO OUTPUT ROUTING:\n" + "\n".join(lines)

    async def broadcast_routing_update(self):
        content = self.output_routing()
        print(f"[BMD PROTOCOL] >> VIDEO OUTPUT ROUTING (broadcast):\n{content}")
        for client in list(self.clients):
            try:
                self.send(client, content)
                await client.drain()
            except Exception as e:
                print(f"[BMD PROTOCOL] Failed to notify client: {e}")
                self.clients.discard(client)

    async def process_block(self, lines, writer):
        if not lines:
            return

        header = lines[0]
        body = lines[1:]

        if header == "PING:":
            self.send(writer, "ACK")
            await writer.drain()
            return

        if header.endswith(":") and not body:
            known = {
                "OUTPUT LABELS": self.output_labels,
                "INPUT LABELS": self.input_labels,
                "VIDEO OUTPUT ROUTING": self.output_routing,
                "VIDEOHUB DEVICE": self.device_info,
            }
            if header in known:
                self.send(writer, "ACK")
                self.send(writer, known[header]())
                await writer.drain()
                return

        if header == "VIDEO OUTPUT ROUTING:":
            changed = []
            for line in body:
                try:
                    out_idx, in_idx = map(int, line.split())
                    receiver_id = self.output_index_map[out_idx]
                    sender_id = self.input_index_map[in_idx]
                    self.routing[receiver_id] = sender_id
                    await emit_patch(sender_id, receiver_id, origin="BMD")
                    changed.append(f"{out_idx} {in_idx}")
                    print(f"[BMD PROTOCOL] Patched output {out_idx} ← input {in_idx} (logical {receiver_id} ← {sender_id})")
                except Exception as e:
                    print(f"[BMD PROTOCOL] Failed to parse line '{line}': {e}")

            self.send(writer, "ACK")
            if changed:
                self.send(writer, "VIDEO OUTPUT ROUTING:\n" + "\n".join(changed))
            await writer.drain()
            await self.broadcast_routing_update()
        else:
            self.send(writer, "NAK")
            await writer.drain()

    async def set_routing(self, sender_id, receiver_id, origin="external", force_broadcast=False):
        current = self.routing.get(receiver_id)
        if current == sender_id and not force_broadcast:
            print(f"[BMD PROTOCOL] No update needed from {origin}: {receiver_id} already routed to {sender_id}")
            return

        self.routing[receiver_id] = sender_id
        print(f"[BMD PROTOCOL] Update from {origin}: {receiver_id} ← {sender_id} (was {current})")
        await self.broadcast_routing_update()

    async def reload_and_broadcast(self):
        self.load_labels()
        await self.refresh_routing_from_nmos()
        await self.broadcast_routing_update()
        print("[BMD PROTOCOL] Reloaded logical labels and broadcasted update.")

    async def refresh_routing_from_nmos(self):
        try:
            await asyncio.to_thread(refresh_discovery)
            cache = read_cache()
            logicals = load_logical_ids()
            receivers_cache = cache.get("receivers", [])
            matched = 0

            for receiver_name, receiver_info in logicals.get("receivers", {}).items():
                receiver_id = receiver_info.get("id")
                found = False
                for source_name, source_info in logicals.get("sources", {}).items():
                    sender_match = True
                    for essence in ["video", "audio", "data"]:
                        sender_id = source_info.get(essence)
                        receiver_uuid = receiver_info.get(essence)

                        if not sender_id or not receiver_uuid:
                            continue

                        receiver_obj = next((r for r in receivers_cache if r.get("id") == receiver_uuid), None)
                        if not receiver_obj:
                            print(f"[BMD MATCH] Receiver {receiver_name} missing from cache (UUID={receiver_uuid})")
                            sender_match = False
                            break

                        actual_sender = receiver_obj.get("subscription", {}).get("sender_id")
                        if actual_sender != sender_id:
                            print(f"[BMD MATCH] Mismatch for {receiver_name}: expected {sender_id}, got {actual_sender}")
                            sender_match = False
                            break

                    if sender_match:
                        self.routing[receiver_id] = source_info.get("id")
                        print(f"[BMD SYNC] {receiver_name} ← {source_name}")
                        matched += 1
                        found = True
                        break

                if not found:
                    print(f"[BMD SYNC] No matching source found for receiver: {receiver_name}")

            print(f"[BMD PROTOCOL] Routing sync completed: {matched} logical group(s) matched.")
        except Exception as e:
            print(f"[BMD PROTOCOL] Error syncing NMOS routing: {e}")