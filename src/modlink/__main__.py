from .runtime import ModLinkRuntime


def main() -> None:
    runtime = ModLinkRuntime()
    print(
        "ModLink runtime initialized",
        f"(devices={len(runtime.devices)}, streams={len(runtime.bus.descriptors())})",
    )


if __name__ == "__main__":
    main()
