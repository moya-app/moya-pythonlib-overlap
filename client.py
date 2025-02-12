import argparse
import asyncio

from httpx import AsyncClient

from moya.overlap.client_httpx import HTTPClientHelper


async def main() -> None:
    parser = argparse.ArgumentParser(description="Perform secure phone number overlap queries against the Moya API")
    parser.add_argument("-t", "--token", help="OAuth token")
    parser.add_argument("-u", "--url", default="https://api.moya.app/v1/overlap", help="Remote URL to connect to")
    parser.add_argument("number_file", help="File containing an internationalized phone number on each line to query")
    args = parser.parse_args()

    with open(args.number_file, "r") as f:
        client_set = [int(i) for i in f.read().splitlines()]

    headers = {"Authorization": f"Bearer {args.token}"} if args.token else {}
    async with AsyncClient(base_url=args.url, timeout=600, headers=headers) as http_client:
        client_helper = HTTPClientHelper(http_client)
        # A new private key is automatically generated each time this is used
        c = await client_helper.get_client()

        overlapped_numbers = await c.get_intersection(client_set)
        print(f"Found {len(overlapped_numbers)} overlapped numbers:")
        for number in overlapped_numbers:
            print(f"    {number}")


if __name__ == "__main__":
    asyncio.run(main())
