def remove_secondary_streams(sdp: str) -> str:
    """
    Delete secondary streams in SDP 'a=group:DUP'.
    Keep only first MID of group DUP.
    """
    lines = sdp.splitlines()
    new_lines = []
    skip_mids = set()

    for line in lines:
        if line.startswith("a=group:DUP"):
            mids = line.strip().split()[1:]
            skip_mids.update(mids[1:])
            continue

    current_mid = None
    buffer = []

    for line in lines:
        if line.startswith("m="):
            if buffer:
                if current_mid not in skip_mids:
                    new_lines.extend(buffer)
                buffer = []
                current_mid = None
        if line.startswith("a=mid:"):
            current_mid = line.strip().split(":")[1]
        buffer.append(line)

    if buffer and current_mid not in skip_mids:
        new_lines.extend(buffer)

    return "\r\n".join(new_lines) + "\r\n"
