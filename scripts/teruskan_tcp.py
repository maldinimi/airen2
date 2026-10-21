"""Penerus TCP sederhana (khusus dev): port 5432 kontainer ini → <host> <port> di jaringan internal.

Dipakai layanan `db-gui` (docker-compose.dev.yml) agar aplikasi GUI database di laptop (DBeaver, pgAdmin)
dapat mengakses PostgreSQL, sementara kontainer `db` tetap hanya di jaringan `internal` tanpa jalur keluar (B1).
Input: argumen `<host> <port>` tujuan. Tidak menyimpan data dan tidak menghubungi alamat lain.
"""
import asyncio
import sys

TUJUAN_HOST, TUJUAN_PORT = sys.argv[1], int(sys.argv[2])


async def salurkan(baca: asyncio.StreamReader, tulis: asyncio.StreamWriter) -> None:
    try:
        while data := await baca.read(65536):
            tulis.write(data)
            await tulis.drain()
    except ConnectionError:
        pass
    finally:
        tulis.close()


async def tangani(baca: asyncio.StreamReader, tulis: asyncio.StreamWriter) -> None:
    try:
        baca_db, tulis_db = await asyncio.open_connection(TUJUAN_HOST, TUJUAN_PORT)
    except OSError:
        tulis.close()
        return
    await asyncio.gather(salurkan(baca, tulis_db), salurkan(baca_db, tulis))


async def utama() -> None:
    server = await asyncio.start_server(tangani, "0.0.0.0", 5432)
    print(f"meneruskan :5432 -> {TUJUAN_HOST}:{TUJUAN_PORT}", flush=True)
    async with server:
        await server.serve_forever()


asyncio.run(utama())
