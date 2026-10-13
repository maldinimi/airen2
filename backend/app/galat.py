"""Error aplikasi dengan pesan ramah (Bahasa Indonesia) untuk pengguna."""


class Galat(Exception):
    def __init__(self, status: int, pesan: str):
        super().__init__(pesan)
        self.status = status
        self.pesan = pesan
