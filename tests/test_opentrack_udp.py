# Copyright (c) 2026 Neyvan Santos. Todos os direitos reservados.
import socket
import struct

from eye_drive_tracker.output.opentrack_udp import OpenTrackUdpOutput
from eye_drive_tracker.tracking.models import PoseSample


def test_opentrack_udp_sends_generic_udp_pose(monkeypatch) -> None:
    sent: list[tuple[bytes, tuple[str, int]]] = []

    class Socket:
        def sendto(self, packet: bytes, address: tuple[str, int]) -> None:
            sent.append((packet, address))

        def close(self) -> None:
            pass

    monkeypatch.setattr(socket, "socket", lambda *_args, **_kwargs: Socket())

    output = OpenTrackUdpOutput()

    assert output.start() == "OpenTrack UDP active"
    assert output.send(PoseSample(yaw=4.0, pitch=5.0, roll=6.0, x=1.0, y=2.0, z=3.0)) == "OpenTrack UDP active"

    packet, address = sent[-1]
    assert address == ("127.0.0.1", 4242)
    assert struct.unpack("<6d", packet) == (1.0, 2.0, 3.0, 4.0, 5.0, 6.0)
