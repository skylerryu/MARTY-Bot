from bot import client
from bot_config import TOKEN


def main():
    print("Starting M.A.R.T.Y...")

    client.run(TOKEN)


if __name__ == "__main__":
    main()