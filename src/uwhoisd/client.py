"""Client."""

import asyncio


async def query_whois(host: str, port: int, query: str) -> str:
    reader, writer = await asyncio.open_connection(host, port)

    writer.write(f"{query}\r\n".encode())
    await writer.drain()

    response = await asyncio.wait_for(reader.read(), timeout=5)

    writer.close()
    await writer.wait_closed()

    return str(response, "utf-8", "ignore")
