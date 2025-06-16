# /services/patch_bus.py
# by Arnaud Cresp - 2025

import asyncio
import aiohttp
from services.logical import get_logical_pair, load_logical_ids
from services.data_loader import load_nodes
from services.nmos_connection import load_receivers_and_sources
from services.nmos_connection import change_source

async def emit_patch(sender_id, receiver_id, origin="external"):
    print(f"[PATCH] {origin}: {receiver_id} ← {sender_id}")

    src, dst = get_logical_pair(sender_id, receiver_id)
    result = {}

    nodes = load_nodes()
    receivers, sources = load_receivers_and_sources(nodes)

    async with aiohttp.ClientSession() as session:
        async def patch_one(essence, sender, receiver):
            try:
                patch_result = await change_source(
                    nodes,
                    receiver,
                    sender,
                    session=session,
                    receivers=receivers,
                    sources=sources
                )
                return (essence, {
                    "status": patch_result.get("status"),
                    "sender": sender,
                    "receiver": receiver,
                    "message": patch_result.get("message", "")
                })
            except Exception as e:
                return (essence, {
                    "status": "error",
                    "sender": sender,
                    "receiver": receiver,
                    "message": str(e)
                })

        tasks = []
        for essence in ["video", "audio", "data"]:
            s = src.get(essence)
            d = dst.get(essence)
            if s and d:
                tasks.append(patch_one(essence, s, d))
            else:
                result[essence] = {
                    "status": "skipped",
                    "reason": "missing sender or receiver"
                }

        results = await asyncio.gather(*tasks)
        for essence, data in results:
            result[essence] = data

    # Notify emulators with logical ID mapping
    try:
        import builtins
        logicals = load_logical_ids()

        source_map = {
            v.get("video"): v.get("id")
            for v in logicals.get("sources", {}).values()
            if isinstance(v.get("id"), int) and v.get("video")
        }

        receiver_map = {
            v.get("video"): v.get("id")
            for v in logicals.get("receivers", {}).values()
            if isinstance(v.get("id"), int) and v.get("video")
        }

        bmd = getattr(builtins, "videohub_emulator", None)
        ross = getattr(builtins, "rosstalk_emulator", None)

        for essence in ["video", "audio", "data"]:
            s = src.get(essence)
            d = dst.get(essence)
            s_logical = source_map.get(s)
            d_logical = receiver_map.get(d)

            if s_logical is not None and d_logical is not None:
                if bmd:
                    await bmd.set_routing(s_logical, d_logical, origin=origin, force_broadcast=(origin != "BMD"))
                if ross:
                    await ross.set_routing(s_logical, d_logical, origin=origin, force_broadcast=(origin != "RossTalk"))
    except Exception as e:
        print(f"[PATCH] Warning: Failed to notify emulator(s): {e}")

    return result