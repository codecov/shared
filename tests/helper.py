from json import dumps


def v2_to_v3(report):
    def _sessions(sessions):
        if sessions:
            return [
                [int(sid), data.get("p") or data["c"], data.get("b")]
                for sid, data in sessions.items()
            ]
        return None

    files = {}
    chunks = []
    for loc, (fname, data) in enumerate(report.get("files", {}).items()):
        totals = data.get("t", {}).get
        files[fname] = [
            loc,
            [totals(k, 0) for k in "fnhmpcbdMs"] if totals("n") else None,
        ]
        chunk = [""]
        if data.get("l"):
            lines = data["l"].get
            for ln in range(1, max(list(map(int, list(data["l"].keys())))) + 1):
                line = lines(str(ln))
                if line:
                    chunk.append(
                        dumps(
                            [
                                line.get("c"),
                                line.get("t"),
                                _sessions(line.get("s")),
                                None,
                            ]
                        )
                    )
                else:
                    chunk.append("")
        chunks.append("\n".join(chunk))

    return {
        "files": files,
        "sessions": dict(
            [(int(sid), data) for sid, data in report.get("sessions", {}).items()]
        ),
        "totals": report.get("totals", {}),
        "chunks": chunks,
    }
