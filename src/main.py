from player.vlc_runtime import bootstrap_vlc_runtime


def main():
    bootstrap_vlc_runtime()

    from player.app import main as app_main

    app_main()


if __name__ == "__main__":
    main()
