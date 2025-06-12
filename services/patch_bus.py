# /services/patch_bus.py
# by Arnaud Cresp - 2025

import asyncio

async def emit_patch(sender_id, receiver_id, origin="external"):
    print(f"[PATCH] {origin}: {receiver_id} ← {sender_id}")

    from services.logical import get_logical_pair
    from services.data_loader import load_nodes
    from services.nmos_connection import change_source

    src, dst = get_logical_pair(sender_id, receiver_id)
    result = {}

    nodes = load_nodes()

    async def patch_one(essence, sender, receiver):
        try:
            patch_result = await asyncio.to_thread(change_source, nodes, receiver, sender)
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

    return result
