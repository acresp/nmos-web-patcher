# /protocols/bmdvideohub.py
# by Arnaud Cresp - 2025

import asyncio
from __version__ import __version__
from services.logical import load_logical_ids
from services.cache import read_cache, wait_cache_ready
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
        self._running_task = None
        self.load_labels()

    def load_labels(self):
        logicals = load_logical_ids()
        sources = logicals.get("sources", {})
        receivers = logicals.get("receivers", {})

        self.inputs = {v["id"]: k for k, v in sources.items() if "id" in v and k}
        self.outputs = {v["id"]: k for k, v in receivers.items() if "id" in v and k}
        self.routing = {}

    async def start(self):
        await asyncio.to_thread(wait_cache_ready, 30)

        await self.sync_from_cache()
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
            except Exception:
                pass
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
        except (ConnectionResetError, BrokenPipeError):
            return

        await self.broadcast_routing_update()

        buffer = []
        try:
            while not reader.at_eof():
                line = await reader.readline()
                if not line:
                    break
                line = line.decode().strip()
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
            except Exception:
                pass

    def send(self, writer, content: str):
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
            f"Video inputs: {len(self.inputs)}\n"
            "Video processing units: 0\n"
            f"Video outputs: {len(self.outputs)}\n"
            "Video monitoring outputs: 0\n"
            "Serial ports: 0"
        )

    def input_labels(self):
        lines = [f"{i} {name}" for i, (i_id, name) in enumerate(sorted(self.inputs.items()))]
        return "INPUT LABELS:\n" + "\n".join(lines)

    def output_labels(self):
        lines = [f"{i} {name}" for i, (i_id, name) in enumerate(sorted(self.outputs.items()))]
        return "OUTPUT LABELS:\n" + "\n".join(lines)

    def output_routing(self):
        lines = []
        for receiver_id, receiver_name in sorted(self.outputs.items()):
            sender_id = self.routing.get(receiver_id)
            if sender_id is not None and sender_id in self.inputs:
                lines.append(f"{receiver_id} {sender_id}")
        return "VIDEO OUTPUT ROUTING:\n" + "\n".join(lines)

    async def broadcast_routing_update(self):
        content = self.output_routing()
        for client in list(self.clients):
            try:
                self.send(client, content)
                await client.drain()
            except Exception:
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
                    receiver_id = out_idx
                    sender_id = in_idx
                    if receiver_id in self.outputs and sender_id in self.inputs:
                        self.routing[receiver_id] = sender_id
                        await emit_patch(sender_id, receiver_id, origin="BMD")
                        changed.append(f"{receiver_id} {sender_id}")
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
            return
        self.routing[receiver_id] = sender_id
        await self.broadcast_routing_update()

    async def reload_and_broadcast(self):
        self.load_labels()
        await self.sync_from_cache()
        await self.broadcast_routing_update()

    async def sync_from_cache(self):
        try:
            cache = read_cache()
            logicals = load_logical_ids()

            receivers_cache = cache.get("receivers", [])
            sources_cache = cache.get("sources", [])

            receivers_by_id = {r.get("id"): r for r in receivers_cache if r.get("id")}
            sources_by_uuid = {s.get("id"): s for s in sources_cache if s.get("id")}

            uuid_to_input_id = {}
            for src_name, src_info in (logicals.get("sources") or {}).items():
                src_input_id = src_info.get("id")
                if src_input_id is None:
                    continue
                for essence in ("video", "audio", "data"):
                    u = src_info.get(essence)
                    if u:
                        uuid_to_input_id[u] = src_input_id

            matched = 0
            unresolved = 0

            def pick_receiver_uuid(rec_info: dict):
                return rec_info.get("video") or rec_info.get("audio") or rec_info.get("data")

            for recv_name, recv_info in (logicals.get("receivers") or {}).items():
                out_id = recv_info.get("id")
                nmos_recv_uuid = pick_receiver_uuid(recv_info)
                if out_id is None or not nmos_recv_uuid:
                    unresolved += 1
                    continue

                recv_obj = receivers_by_id.get(nmos_recv_uuid)
                if not recv_obj:
                    unresolved += 1
                    continue

                sub = recv_obj.get("subscription") or {}
                sender_uuid = sub.get("sender_id")
                if not sender_uuid:
                    unresolved += 1
                    continue

                input_id = uuid_to_input_id.get(sender_uuid)
                if input_id is None:
                    unresolved += 1
                    continue

                self.routing[out_id] = input_id
                matched += 1

            print(f"[BMD PROTOCOL] Routing sync completed: {matched} routes matched, {unresolved} unresolved.")
        except Exception as e:
            print(f"[BMD PROTOCOL] Error syncing NMOS routing: {e}")