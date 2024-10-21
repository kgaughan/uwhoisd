import asyncio

from . import utils


async def start_service(iface: str, port: int, whois):
    async def handle_request(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        query = await reader.readuntil(b"\r\n")
        cleaned = query.decode().strip().lower()
        if not utils.is_well_formed_fqdn(cleaned):
            result = f"; Bad query: '{cleaned}'\r\n"
        else:
            result = await whois(cleaned)
        writer.write(result.encode())
        await writer.drain()
        writer.close()

    svr = await asyncio.start_server(handle_request, host=iface, port=port)
    async with svr:
        await svr.serve_forever()
