"""Client."""

import asyncio


async def query_whois(host: str, port: int, query: str) -> str:
    """Query a WHOIS server.

    Args:
        host: The WHOIS server hostname.
        port: The WHOIS server port.
        query: The WHOIS query.

    Returns:
        The WHOIS response.
    """
    reader, writer = await asyncio.open_connection(host, port)

    writer.write(f"{query}\r\n".encode())
    await writer.drain()

    response = await asyncio.wait_for(reader.read(), timeout=5)

    writer.close()
    await writer.wait_closed()

    return str(response, "utf-8", "ignore")
