from settings import Settings


def main() -> None:
    """Main entrypoint."""
    settings = Settings()
    print(f"Loaded settings: {settings.app_name}")


if __name__ == "__main__":
    main()
