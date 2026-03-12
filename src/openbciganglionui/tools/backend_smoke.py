from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PyQt6.QtCore import QObject, QCoreApplication, QTimer

from ..backend import (
    BrainFlowGanglionBackend,
    ConnectConfig,
    DeviceSearchResult,
    DeviceState,
    ErrorEvent,
    MarkerEvent,
    RecordEvent,
    RecordSession,
    SearchEvent,
    StateEvent,
    StreamChunk,
)


NATIVE_BLE_METHOD = "Native BLE"
DONGLE_METHOD = "Ganglion Dongle"


@dataclass(slots=True)
class SmokeSummary:
    search_results: int = 0
    chunks_received: int = 0
    samples_received: int = 0
    record_started: bool = False
    record_stopped: bool = False
    marker_emitted: bool = False
    first_chunk_shape: tuple[int, int] | None = None
    first_chunk_fs: float | None = None


class BackendSmokeRunner(QObject):
    def __init__(self, args: argparse.Namespace, parent: QObject | None = None) -> None:
        super().__init__(parent=parent)
        self.args = args
        self.app = QCoreApplication.instance()
        if self.app is None:
            raise RuntimeError("QCoreApplication must be created before BackendSmokeRunner")

        self.backend = BrainFlowGanglionBackend(parent=self)
        self.summary = SmokeSummary()
        self._selected_result: DeviceSearchResult | None = None
        self._preview_window_started = False
        self._record_stop_scheduled = False
        self._disconnect_requested = False
        self._finished = False
        self._exit_code = 0

        self.backend.sig_state.connect(self._on_state)
        self.backend.sig_search.connect(self._on_search)
        self.backend.sig_stream.connect(self._on_stream)
        self.backend.sig_record.connect(self._on_record)
        self.backend.sig_marker.connect(self._on_marker)
        self.backend.sig_error.connect(self._on_error)

        total_timeout_ms = int(
            max(
                15.0,
                float(self.args.timeout_sec) * 2
                + float(self.args.preview_sec)
                + float(self.args.record_sec)
                + 10.0,
            )
            * 1000
        )
        QTimer.singleShot(total_timeout_ms, self._on_timeout)

    def start(self) -> None:
        self._log("=== Backend smoke test ===")
        self._log(f"method={self.args.method}")
        self._log(f"search={self._should_search()}")
        self._log(f"preview_sec={self.args.preview_sec}")
        self._log(f"record_sec={self.args.record_sec}")
        self._log(f"save_dir={self._save_dir()}")

        if self._should_search():
            self.backend.search_devices(self.args.method)
            return

        self._connect(None)

    def shutdown(self) -> None:
        self.backend._shutdown_worker_thread()

    def _should_search(self) -> bool:
        if self.args.search:
            return True
        if self.args.method == NATIVE_BLE_METHOD:
            return not any(
                [
                    self.args.device_address,
                    self.args.mac_address,
                    self.args.serial_number,
                ]
            )
        return not any([self.args.serial_port, self.args.device_address])

    def _connect(self, result: DeviceSearchResult | None) -> None:
        self._selected_result = result
        config = ConnectConfig(
            connection_method=self.args.method,
            device_name=self.args.device_name or (result.name if result else "Ganglion"),
            device_address=self.args.device_address or (result.address if result else ""),
            serial_port=self.args.serial_port or (result.serial_port if result else ""),
            mac_address=self.args.mac_address or (result.mac_address if result else ""),
            serial_number=self.args.serial_number or (result.serial_number if result else ""),
            firmware_hint=self.args.firmware_hint,
            timeout_sec=int(self.args.timeout_sec),
            chunk_size=int(self.args.chunk_size),
        )
        self._log(
            "connect config:"
            f" name={config.device_name!r}"
            f" address={config.device_address!r}"
            f" serial_port={config.serial_port!r}"
            f" mac={config.mac_address!r}"
            f" serial_number={config.serial_number!r}"
        )
        self.backend.connect_device(config)

    def _start_record(self) -> None:
        session_id = time.strftime("smoke_%Y%m%d_%H%M%S")
        session = RecordSession(
            session_id=session_id,
            save_dir=self._save_dir(),
            subject_id=self.args.subject_id,
            task_name=self.args.task_name,
        )
        self._log(
            f"start record: session_id={session.session_id} subject={session.subject_id} task={session.task_name}"
        )
        self.backend.start_record(session)

    def _request_disconnect(self) -> None:
        if self._disconnect_requested:
            return
        self._disconnect_requested = True
        self._log("disconnect requested")

        if self.backend.state in {
            DeviceState.CONNECTED,
            DeviceState.PREVIEWING,
            DeviceState.RECORDING,
        }:
            self.backend.disconnect_device()
            return

        self._finish(self._exit_code)

    def _on_search(self, event: SearchEvent) -> None:
        if event.is_searching:
            self._log(f"search started: method={event.method}")
            return

        self.summary.search_results = len(event.results)
        self._log(f"search finished: {len(event.results)} result(s)")
        for index, result in enumerate(event.results, start=1):
            self._log(
                f"  [{index}] name={result.name!r} address={result.address!r} "
                f"serial_port={result.serial_port!r} mac={result.mac_address!r} "
                f"serial_number={result.serial_number!r}"
            )

        selected = self._select_result(event.results)
        if selected is None:
            self._fail("search completed but no usable device candidate was found")
            return
        self._connect(selected)

    def _on_state(self, event: StateEvent) -> None:
        self._log(f"state={event.state.value} message={event.message!r}")

        if event.state == DeviceState.PREVIEWING and not self._preview_window_started:
            self._preview_window_started = True
            QTimer.singleShot(int(max(0.0, float(self.args.preview_sec)) * 1000), self._after_preview_window)
            return

        if event.state == DeviceState.DISCONNECTED and self._disconnect_requested:
            self._finish(self._exit_code)

    def _on_stream(self, chunk: StreamChunk) -> None:
        self.summary.chunks_received += 1
        self.summary.samples_received += int(chunk.data.shape[0])
        if self.summary.first_chunk_shape is None:
            self.summary.first_chunk_shape = tuple(int(value) for value in chunk.data.shape)
            self.summary.first_chunk_fs = float(chunk.fs)
            self._log(
                f"first chunk: shape={self.summary.first_chunk_shape} fs={self.summary.first_chunk_fs:.1f}"
            )

    def _on_record(self, event: RecordEvent) -> None:
        self._log(
            f"record event: is_recording={event.is_recording} session_id={event.session_id!r} "
            f"sample_index={event.sample_index}"
        )

        if event.is_recording:
            self.summary.record_started = True
            if self.args.marker_label:
                marker_delay_ms = int(max(0.5, float(self.args.record_sec) * 0.5) * 1000)
                QTimer.singleShot(marker_delay_ms, self._emit_marker)

            if not self._record_stop_scheduled:
                self._record_stop_scheduled = True
                QTimer.singleShot(
                    int(max(0.5, float(self.args.record_sec)) * 1000),
                    self.backend.stop_record,
                )
            return

        self.summary.record_stopped = True
        self._request_disconnect()

    def _on_marker(self, event: MarkerEvent) -> None:
        self.summary.marker_emitted = True
        self._log(
            f"marker emitted: label={event.label!r} sample_index={event.sample_index} note={event.note!r}"
        )

    def _on_error(self, event: ErrorEvent) -> None:
        self._fail(
            f"backend error: code={event.code} message={event.message} detail={event.detail}"
        )

    def _after_preview_window(self) -> None:
        if self.summary.chunks_received <= 0:
            self._fail("preview state was reached but no stream chunk was received")
            return

        if float(self.args.record_sec) <= 0:
            self._log("preview smoke passed, skipping record step")
            self._request_disconnect()
            return

        self._start_record()

    def _emit_marker(self) -> None:
        if self.backend.state != DeviceState.RECORDING:
            return
        if self.summary.marker_emitted:
            return
        self.backend.add_marker(self.args.marker_label, note="smoke_test")

    def _on_timeout(self) -> None:
        self._fail("smoke test timed out")

    def _select_result(
        self,
        results: Iterable[DeviceSearchResult],
    ) -> DeviceSearchResult | None:
        result_list = list(results)
        if not result_list:
            return None

        wanted = {
            value.strip().lower()
            for value in (
                self.args.device_address,
                self.args.serial_port,
                self.args.mac_address,
                self.args.serial_number,
            )
            if value.strip()
        }
        if not wanted:
            return result_list[0]

        for result in result_list:
            candidates = {
                value.strip().lower()
                for value in (
                    result.address,
                    result.serial_port,
                    result.mac_address,
                    result.serial_number,
                )
                if value.strip()
            }
            if wanted & candidates:
                return result
        return None

    def _save_dir(self) -> str:
        return str(Path(self.args.save_dir).expanduser().resolve())

    def _fail(self, reason: str) -> None:
        if self._finished:
            return
        self._exit_code = 1
        self._log(f"FAIL: {reason}")
        self._request_disconnect()

    def _finish(self, exit_code: int) -> None:
        if self._finished:
            return

        self._finished = True
        self._log("=== Summary ===")
        self._log(f"search_results={self.summary.search_results}")
        self._log(f"chunks_received={self.summary.chunks_received}")
        self._log(f"samples_received={self.summary.samples_received}")
        self._log(f"first_chunk_shape={self.summary.first_chunk_shape}")
        self._log(f"first_chunk_fs={self.summary.first_chunk_fs}")
        self._log(f"record_started={self.summary.record_started}")
        self._log(f"record_stopped={self.summary.record_stopped}")
        self._log(f"marker_emitted={self.summary.marker_emitted}")
        QTimer.singleShot(0, lambda: self.app.exit(exit_code))

    def _log(self, message: str) -> None:
        print(message, flush=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Simple smoke test for the BrainFlow Ganglion backend.")
    parser.add_argument(
        "--method",
        choices=("native", "dongle"),
        default="native",
        help="Connection transport to test.",
    )
    parser.add_argument(
        "--search",
        action="store_true",
        help="Run backend.search_devices() before connecting.",
    )
    parser.add_argument("--device-name", default="", help="Preferred device name for display.")
    parser.add_argument("--device-address", default="", help="Preferred device address.")
    parser.add_argument("--serial-port", default="", help="Dongle serial port, for example COM3.")
    parser.add_argument("--mac-address", default="", help="Native BLE MAC address, used only for manual diagnostics.")
    parser.add_argument("--serial-number", default="", help="Native BLE serial number, typically the device name.")
    parser.add_argument(
        "--firmware-hint",
        choices=("auto", "2", "3"),
        default="auto",
        help="BrainFlow firmware hint for Ganglion devices.",
    )
    parser.add_argument("--timeout-sec", type=int, default=5, help="Connect/search timeout in seconds.")
    parser.add_argument("--chunk-size", type=int, default=20, help="Requested stream chunk size.")
    parser.add_argument("--preview-sec", type=float, default=5.0, help="Preview duration before record step.")
    parser.add_argument("--record-sec", type=float, default=3.0, help="Clip recording duration. Use 0 to skip.")
    parser.add_argument("--marker-label", default="smoke_marker", help="Marker label inserted during recording.")
    parser.add_argument(
        "--save-dir",
        default="data/smoke_tests",
        help="Root directory for smoke-test recordings.",
    )
    parser.add_argument("--subject-id", default="smoke_subject", help="Subject ID used for the smoke-test clip.")
    parser.add_argument("--task-name", default="smoke_clip", help="Task name used for the smoke-test clip.")
    return parser


def normalize_args(args: argparse.Namespace) -> argparse.Namespace:
    args.method = NATIVE_BLE_METHOD if args.method == "native" else DONGLE_METHOD
    args.device_name = str(args.device_name).strip()
    args.device_address = str(args.device_address).strip()
    args.serial_port = str(args.serial_port).strip()
    args.mac_address = str(args.mac_address).strip()
    args.serial_number = str(args.serial_number).strip()
    args.marker_label = str(args.marker_label).strip()
    args.subject_id = str(args.subject_id).strip() or "smoke_subject"
    args.task_name = str(args.task_name).strip() or "smoke_clip"
    args.save_dir = str(args.save_dir).strip() or "data/smoke_tests"
    return args


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = normalize_args(parser.parse_args(argv))

    app = QCoreApplication(sys.argv[:1] if argv is None else ["backend-smoke", *argv])
    runner = BackendSmokeRunner(args)
    runner.start()
    exit_code = app.exec()
    runner.shutdown()
    return int(exit_code)


if __name__ == "__main__":
    raise SystemExit(main())
