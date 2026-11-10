"""Boot the real desktop bridge with outbound I/O disabled and verify its protocol."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile


OFFLINE_HOST = """
import runpy
import sys

def offline(event, args):
    if event in {
        'socket.connect', 'socket.getaddrinfo', 'socket.gethostbyname',
        'socket.gethostbyname_ex', 'socket.sendto', 'subprocess.Popen',
        'os.system', 'os.startfile',
    }:
        raise OSError('Network and subprocesses are disabled for this smoke test')

sys.addaudithook(offline)
sys.argv = sys.argv[1:]
runpy.run_path(sys.argv[0], run_name='__main__')
"""


def smoke(python: Path, host: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="aurora-smoke-") as folder:
        state = Path(folder) / "state"
        requests = [
            {"id": 1, "method": "getCognitiveStats"},
            {"id": 2, "method": "getPraxisStatus"},
            {"id": 3, "method": "habitatGetState", "args": {
                "params": json.dumps({"territory": "space", "actor": "human"}),
            }},
        ]
        with (Path(folder) / "boot.log").open("w+b") as boot_log:
            try:
                proc = subprocess.run(
                    [str(python), "-I", "-X", "utf8", "-u", "-c", OFFLINE_HOST,
                     str(host), str(state)],
                    input="".join(json.dumps(item) + "\n" for item in requests),
                    stdout=subprocess.PIPE, stderr=boot_log,
                    encoding="utf-8", timeout=720, check=True,
                )
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                stage = state / "last_boot_stage.txt"
                if stage.is_file():
                    print(stage.read_text(encoding="utf-8"), file=sys.stderr)
                boot_log.seek(0, 2)
                boot_log.seek(max(0, boot_log.tell() - 8192))
                print(boot_log.read().decode("utf-8", errors="replace"), file=sys.stderr)
                raise

        records = [json.loads(line) for line in proc.stdout.splitlines()]
        ready = [record["event"] for record in records if record.get("event", {}).get("type") == "ready"]
        assert ready and ready[0]["health"]["overall"] in {"healthy", "degraded"}, records
        replies = {record["id"]: json.loads(record["value"]) for record in records if "id" in record}
        assert replies[1] and replies[2].get("status") != "not_initialized"
        assert replies[3].get("territory") == "space", replies[3]
        print(f"Aurora booted ({ready[0]['health']['overall']}); metrics, Praxis and Habitat returned data")


if __name__ == "__main__":
    smoke(Path(sys.argv[1]).absolute(), Path(sys.argv[2]).absolute())
