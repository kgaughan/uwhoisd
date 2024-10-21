import asyncio

from . import utils


async def start_service(iface: str, port: int, whois):
    async def handle_request(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        try:
            query = await asyncio.wait_for(reader.readuntil(b"\r\n"), timeout=5)
        except asyncio.TimeoutError:
            writer.write(b"; Query timeout: closing\r\n")
            await writer.drain()
            writer.close()
            return

        cleaned = query.decode().strip().lower()
        if not utils.is_well_formed_fqdn(cleaned):
            result = f"; Bad query: '{cleaned}'\r\n"
        else:
            try:
                result = await whois(cleaned)
            except asyncio.TimeoutError:
                result = "; Timeout from upstream server\r\n"
        writer.write(result.encode())
        await writer.drain()
        writer.close()

    svr = await asyncio.start_server(handle_request, host=iface, port=port)
    async with svr:
        await svr.serve_forever()
