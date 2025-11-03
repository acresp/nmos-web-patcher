# /services/patch_bus.py
# by Arnaud Cresp - 2025

import json

from services.logical import get_logical_pair, load_logical_ids
from services.data_loader import load_nodes
from services.nmos_connection import change_source, disconnect_receiver
from services.cache import read_cache

CACHE_FILE = "data_cache.json"

# Vérifie si un patch/disconnect est considéré comme réussi
def _is_success(patch_result: dict) -> bool:
    """Détermine si le patch d'une essence est réussi, même si le backend ne renvoie pas strictement 'success'."""
    if not isinstance(patch_result, dict):
        return False

    status = (patch_result.get("status") or "").lower()
    msg = (patch_result.get("message") or "").lower()

    flags = [
        status in ("success", "ok", "applied"),
        patch_result.get("applied"),
        patch_result.get("activated"),
        "patch complete" in msg,
        "receiver patched" in msg,
        "sender activated" in msg,
        "disconnected" in msg,
        "receiver disconnected" in msg,
    ]
    return any(bool(x) for x in flags)

# Applique un patch logique NMOS (ou un disconnect si sender_id=None)
async def emit_patch(sender_id, receiver_id, origin="external"):
    print(f"[PATCH] {origin}: {receiver_id} ← {sender_id}")

    # Gestion du disconnect global (sender_id == "disconnect")
    if sender_id in (None, "disconnect"):
        print(f"[PATCH] {origin}: disconnect request for logical receiver {receiver_id}")

        logicals = load_logical_ids()
        receivers_map = logicals.get("receivers", {})
        receiver_entry = next((v for v in receivers_map.values() if v.get("id") == receiver_id), None)
        if not receiver_entry:
            print(f"[PATCH] No receiver found for logical {receiver_id}")
            return {"status": "error", "message": "logical receiver not found"}

        nodes = load_nodes()
        cache = read_cache()
        disconnected = {}

        for essence in ("video", "audio", "data"):
            receiver_uuid = receiver_entry.get(essence)
            if not receiver_uuid:
                disconnected[essence] = {"status": "skipped", "reason": "no receiver id"}
                continue

            try:
                result = disconnect_receiver(nodes, receiver_uuid, receivers=cache.get("receivers", []))
                disconnected[essence] = result
                print(f"[PATCH] Disconnected {essence.upper()} receiver {receiver_uuid}")
            except Exception as e:
                disconnected[essence] = {"status": "error", "message": str(e)}
                print(f"[PATCH] ERROR disconnect {essence}: {e}")

        # Notifie les émulateurs (si actifs)
        try:
            import builtins
            bmd = getattr(builtins, "videohub_emulator", None)
            ross = getattr(builtins, "rosstalk_emulator", None)
            if bmd:
                await bmd.clear_routing(receiver_id, origin=origin)
            if ross and receiver_id in ross.routing:
                del ross.routing[receiver_id]
                print(f"[ROSS PROTOCOL] Cleared route for {receiver_id}")
        except Exception as e:
            print(f"[PATCH] Warning: emulator notify failed: {e}")

        print(f"[OK] Disconnect complete for logical {receiver_id}")
        return {"status": "ok", "disconnected": disconnected}

    src, dst = get_logical_pair(sender_id, receiver_id)
    result = {"video": {}, "audio": {}, "data": {}}

    nodes = load_nodes()
    cache = read_cache()
    receivers = cache.get("receivers", [])
    sources = cache.get("sources", [])
    print(f"[CACHE] Loaded {len(receivers)} receivers / {len(sources)} sources from cache")

    async def patch_one_in_order(essence: str):
        """Patch NMOS ou disconnect pour une seule essence (video/audio/data)."""
        s = src.get(essence)
        d = dst.get(essence)
        if not d:
            result[essence] = {"status": "skipped", "reason": "missing receiver"}
            return

        if s in (None, ""):
            result[essence] = {"status": "skipped", "reason": "no sender (unchanged)"}
            return

        if s == "disconnect":
            try:
                res = disconnect_receiver(nodes, d, receivers=receivers)
                print(f"[PATCH] Disconnect {essence.upper()} receiver {d}")
                result[essence] = {"status": "success", "receiver": d, "message": "essence disconnected"}
            except Exception as e:
                result[essence] = {"status": "error", "receiver": d, "message": str(e)}
                print(f"[PATCH] ERROR disconnect {essence}: {e}")
            return

        try:
            patch_result = await change_source(
                nodes,
                d,  # receiver UUID NMOS
                s,  # sender UUID NMOS
                receivers=receivers,
                sources=sources
            )
        except Exception as e:
            result[essence] = {"status": "error", "sender": s, "receiver": d, "message": str(e)}
            return

        success = _is_success(patch_result)
        normalized = {
            "status": "success" if success else (patch_result.get("status") or "error"),
            "sender": s,
            "receiver": d,
            "message": patch_result.get("message", "")
        }
        result[essence] = normalized

        if success:
            r_obj = next((r for r in receivers if r.get("id") == d), None)
            if r_obj is not None:
                if "subscription" not in r_obj or not isinstance(r_obj["subscription"], dict):
                    r_obj["subscription"] = {}
                r_obj["subscription"]["sender_id"] = s
                try:
                    with open(CACHE_FILE, "w") as f:
                        json.dump(cache, f, indent=2)
                    print(f"[CACHE] receiver={d} ← sender={s} (essence={essence})")
                except Exception as e:
                    print(f"[CACHE] Failed to write cache update (essence={essence}): {e}")

    # Boucle principale sur les essences
    for essence in ("video", "audio", "data"):
        await patch_one_in_order(essence)

    try:
        import builtins
        logicals = load_logical_ids()

        source_map = {
            v.get("video"): v.get("id")
            for v in (logicals.get("sources") or {}).values()
            if isinstance(v.get("id"), int) and v.get("video")
        }
        receiver_map = {
            v.get("video"): v.get("id")
            for v in (logicals.get("receivers") or {}).values()
            if isinstance(v.get("id"), int) and v.get("video")
        }

        s_logical = source_map.get(src.get("video"))
        d_logical = receiver_map.get(dst.get("video"))

        bmd = getattr(builtins, "videohub_emulator", None)
        ross = getattr(builtins, "rosstalk_emulator", None)

        if s_logical is not None and d_logical is not None:
            if bmd:
                await bmd.set_routing(
                    s_logical, d_logical,
                    origin=origin,
                    force_broadcast=(origin != "BMD")
                )

            if ross:
                current = ross.routing.get(d_logical)
                if current != s_logical:
                    ross.routing[d_logical] = s_logical
                    print(f"[ROSS PROTOCOL] Update from {origin}: {d_logical} ← {s_logical}")

    except Exception as e:
        print(f"[PATCH] Warning: Failed to notify emulator(s): {e}")

    # Résumé des statuts
    ok = [k for k, v in result.items() if v.get("status") in ("success", "ok")]
    ko = [k for k, v in result.items() if v.get("status") not in ("success", "skipped", "ok")]
    if ok:
        print(f"[OK] Patch applied for essences: {', '.join(ok)} (no global refresh)")
    if ko:
        print(f"[WARN] Patch issues for essences: {', '.join(ko)}")

    return result