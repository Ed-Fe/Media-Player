import sys

from player.mpv_runtime import bootstrap_mpv_runtime


def main():
    bootstrap_mpv_runtime()

    initial_paths = sys.argv[1:]

    if initial_paths:
        from player.single_instance import try_send_to_existing_instance

        if try_send_to_existing_instance(initial_paths):
            return

    from player.app import main as app_main

    app_main(initial_paths=initial_paths)


if __name__ == "__main__":
    main()
