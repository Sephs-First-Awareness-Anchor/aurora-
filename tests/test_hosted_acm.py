import socket
import threading
import time

from aurora_acm_bridge import StatusReceiver, HostedACMBridge


def status_frame(tick):
    body = bytes([0xac, 0x53, 100, 110, 120, 130, 140, 2, 3, 4]) + tick.to_bytes(4, 'little')
    checksum = 0
    for byte in body:
        checksum ^= byte
    return body + bytes([checksum])


def test_fragmented_and_batched_statuses_deliver_each_valid_frame_once():
    parser = StatusReceiver()
    a, b = status_frame(10), status_frame(11)
    assert parser.feed(b'junk' + a[:6]) == []
    assert [s['tick'] for s in parser.feed(a[6:] + b)] == [10, 11]
    assert parser.feed(b'') == []
    bad = bytearray(status_frame(12)); bad[-1] ^= 1
    assert [s['tick'] for s in parser.feed(bytes(bad) + status_frame(13))] == [13]
    assert parser.invalid_frames == 1 and parser.frames_recv == 3


def test_tick_wrap_reset_and_duplicate_observations_are_counted_without_fabrication():
    heard = []
    bridge = HostedACMBridge(lambda: {}, heard.append)
    bridge.feed(status_frame(0xfffffffe) + status_frame(1) + status_frame(1) + status_frame(0))
    report = bridge.status()
    assert len(heard) == 4 and report['frames_rx'] == 4
    assert report['skipped_kernel_ticks'] == 2
    assert report['duplicate_tick_statuses'] == 1 and report['kernel_resets'] == 1


def test_hosted_bridge_uses_real_loopback_io_and_stops_cleanly():
    listen = socket.socket()
    listen.bind(('127.0.0.1', 0)); listen.listen()
    received, done = [], threading.Event()
    def kernel():
        connection, _ = listen.accept()
        with connection:
            connection.settimeout(2)
            data = connection.recv(8)
            received.append(data)
            connection.sendall(status_frame(60) + status_frame(61))
            done.wait(2)
    thread = threading.Thread(target=kernel, daemon=True); thread.start()
    heard = []
    bridge = HostedACMBridge(lambda: {'X': .6}, heard.append, port=listen.getsockname()[1])
    try:
        bridge.start()
        end = time.monotonic() + 3
        while len(heard) < 2 and time.monotonic() < end:
            time.sleep(.01)
        assert [s['tick'] for s in heard] == [60, 61]
        assert received[0][:2] == b'\xacX'
        assert bridge.status()['frames_tx'] >= 1
    finally:
        done.set(); bridge.stop(); listen.close(); thread.join(3)
    assert not bridge._thread.is_alive()
