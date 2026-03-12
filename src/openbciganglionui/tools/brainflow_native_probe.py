from __future__ import annotations

import argparse
import platform
import sys
import time
from dataclasses import dataclass
from importlib.metadata import version

import numpy as np
from brainflow.board_shim import BoardIds, BoardShim, BrainFlowError, BrainFlowInputParams
from brainflow.exit_codes import BrainFlowExitCodes


@dataclass(slots=True)
class ProbeAttemptResult:
    firmware_hint: str
    connected: bool
    samples_received: int = 0
    chunks_observed: int = 0
    fs: float = 0.0
    channel_names: tuple[str, ...] = ()
    data_shape: tuple[int, int] | None = None
    message: str = ""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Direct BrainFlow probe for Ganglion Native BLE."
    )
    parser.add_argument("--mac-address", default="", help="Ganglion MAC address.")
    parser.add_argument(
        "--serial-number",
        default="",
        help="Optional Ganglion serial number for BrainFlow native BLE.",
    )
    parser.add_argument(
        "--firmware-hints",
        default="auto,2,3",
        help="Comma-separated firmware hints to try in order. Example: auto,2,3",
    )
    parser.add_argument(
        "--timeout-sec",
        type=int,
        default=8,
        help="BrainFlow connection timeout per attempt.",
    )
    parser.add_argument(
        "--probe-sec",
        type=float,
        default=8.0,
        help="How long to keep the stream running after a successful connection.",
    )
    parser.add_argument(
        "--poll-interval-sec",
        type=float,
        default=0.25,
        help="Polling interval while collecting streamed data.",
    )
    parser.add_argument(
        "--stream-buffer-size",
        type=int,
        default=45000,
        help="BrainFlow start_stream buffer size.",
    )
    parser.add_argument(
        "--log-file",
        default="",
        help="Optional BrainFlow log file path.",
    )
    parser.add_argument(
        "--trace",
        action="store_true",
        help="Enable verbose BrainFlow board logger output.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned attempts without opening the board.",
    )
    return parser


def normalize_firmware_hints(raw_value: str) -> list[str]:
    hints: list[str] = []
    seen: set[str] = set()
    for item in str(raw_value).split(","):
        hint = item.strip().lower()
        if hint not in {"auto", "2", "3"}:
            continue
        if hint in seen:
            continue
        hints.append(hint)
        seen.add(hint)
    return hints or ["auto"]


def build_input_params(args: argparse.Namespace, firmware_hint: str) -> BrainFlowInputParams:
    params = BrainFlowInputParams()
    params.timeout = int(max(1, args.timeout_sec))
    params.other_info = f"fw:{firmware_hint}"
    params.mac_address = str(args.mac_address).strip()
    params.serial_number = str(args.serial_number).strip()
    return params


def resolve_channel_names(board_id: int, channel_count: int) -> tuple[str, ...]:
    descr = BoardShim.get_board_descr(board_id)
    eeg_names = descr.get("eeg_names", "")
    if isinstance(eeg_names, str):
        names = tuple(part.strip() for part in eeg_names.split(",") if part.strip())
        if len(names) >= channel_count:
            return names[:channel_count]
    return tuple(f"ch{index + 1}" for index in range(channel_count))


def format_exit_code(exit_code: int) -> str:
    try:
        code = BrainFlowExitCodes(int(exit_code))
    except (TypeError, ValueError):
        return str(exit_code)
    return f"{code.name}:{int(code.value)}"


def probe_once(args: argparse.Namespace, firmware_hint: str) -> ProbeAttemptResult:
    board_id = int(BoardIds.GANGLION_NATIVE_BOARD.value)
    params = build_input_params(args, firmware_hint)
    board = BoardShim(board_id, params)

    result = ProbeAttemptResult(
        firmware_hint=firmware_hint,
        connected=False,
        message="not started",
    )

    try:
        board.prepare_session()
        result.connected = True
        result.message = "prepare_session succeeded"

        eeg_channels = tuple(int(index) for index in BoardShim.get_eeg_channels(board_id))
        result.fs = float(BoardShim.get_sampling_rate(board_id))
        result.channel_names = resolve_channel_names(board_id, len(eeg_channels))

        board.start_stream(int(max(1024, args.stream_buffer_size)), "")
        started_at = time.monotonic()
        chunks_observed = 0
        sample_count = 0
        last_shape: tuple[int, int] | None = None

        while time.monotonic() - started_at < float(args.probe_sec):
            time.sleep(max(0.05, float(args.poll_interval_sec)))
            board_data = board.get_board_data()
            if board_data is None or getattr(board_data, "size", 0) == 0:
                continue

            eeg_rows = board_data[list(eeg_channels), :]
            if eeg_rows.size == 0:
                continue

            chunk = np.ascontiguousarray(eeg_rows.T, dtype=np.float32)
            chunks_observed += 1
            sample_count += int(chunk.shape[0])
            last_shape = (int(chunk.shape[0]), int(chunk.shape[1]))

        result.samples_received = sample_count
        result.chunks_observed = chunks_observed
        result.data_shape = last_shape
        if sample_count > 0:
            result.message = "stream probe succeeded"
        else:
            result.message = "connected but no EEG samples were received"
        return result
    except BrainFlowError as exc:
        result.message = f"{format_exit_code(exc.exit_code)} {exc}"
        return result
    except Exception as exc:
        result.message = f"{type(exc).__name__}: {exc}"
        return result
    finally:
        try:
            board.stop_stream()
        except Exception:
            pass
        try:
            board.release_session()
        except Exception:
            pass


def print_environment(args: argparse.Namespace, firmware_hints: list[str]) -> None:
    print("=== BrainFlow Native Probe ===", flush=True)
    print(f"python={platform.python_version()}", flush=True)
    print(f"platform={platform.platform()}", flush=True)
    print(f"brainflow={version('brainflow')}", flush=True)
    print(f"mac_address={args.mac_address!r}", flush=True)
    print(f"serial_number={args.serial_number!r}", flush=True)
    print(f"firmware_hints={firmware_hints}", flush=True)
    print(f"timeout_sec={args.timeout_sec}", flush=True)
    print(f"probe_sec={args.probe_sec}", flush=True)


def configure_logger(args: argparse.Namespace) -> None:
    if args.log_file:
        BoardShim.set_log_file(args.log_file)
    if args.trace:
        BoardShim.enable_dev_board_logger()
        return
    BoardShim.enable_board_logger()


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    firmware_hints = normalize_firmware_hints(args.firmware_hints)

    configure_logger(args)
    print_environment(args, firmware_hints)

    if args.dry_run:
        for firmware_hint in firmware_hints:
            params = build_input_params(args, firmware_hint)
            print(
                "planned attempt:"
                f" fw={firmware_hint}"
                f" mac={params.mac_address!r}"
                f" serial_number={params.serial_number!r}"
                f" timeout={params.timeout}",
                flush=True,
            )
        return 0

    results: list[ProbeAttemptResult] = []
    for index, firmware_hint in enumerate(firmware_hints, start=1):
        print(f"--- Attempt {index}/{len(firmware_hints)} fw:{firmware_hint} ---", flush=True)
        result = probe_once(args, firmware_hint)
        results.append(result)
        print(f"connected={result.connected}", flush=True)
        print(f"message={result.message}", flush=True)
        if result.connected:
            print(f"fs={result.fs}", flush=True)
            print(f"channel_names={result.channel_names}", flush=True)
            print(f"chunks_observed={result.chunks_observed}", flush=True)
            print(f"samples_received={result.samples_received}", flush=True)
            print(f"last_chunk_shape={result.data_shape}", flush=True)

        if result.connected and result.samples_received > 0:
            print("SUCCESS: BrainFlow Native BLE path is working.", flush=True)
            return 0

    print("=== Probe Summary ===", flush=True)
    for result in results:
        print(
            f"fw:{result.firmware_hint} connected={result.connected} "
            f"samples={result.samples_received} message={result.message}",
            flush=True,
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
