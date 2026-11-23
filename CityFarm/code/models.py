"""Entidades e valores estáveis do domínio City-Farm."""
from dataclasses import dataclass
import re


FOOD_PRODUCT = "food"
PLAYER_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")


@dataclass(frozen=True)
class PlayerProfile:
    """Identidade casual de um jogador; não representa autenticação."""

    player_id: str
    nickname: str

    @classmethod
    def from_registration(cls, player_id, nickname):
        if not isinstance(player_id, str) or not PLAYER_ID_PATTERN.fullmatch(player_id):
            raise ValueError("Invalid player ID")
        if not isinstance(nickname, str):
            raise ValueError("Invalid nickname")
        nickname = nickname.strip()
        if not 1 <= len(nickname) <= 24 or any(
            not (character.isalnum() or character in " _-") for character in nickname
        ):
            raise ValueError("Nickname must contain 1–24 letters, digits, spaces, _ or -")
        return cls(player_id=player_id, nickname=nickname)

    def as_payload(self):
        """Formato enviado ao cliente pelo WebSocket."""
        return {"id": self.player_id, "name": self.nickname}
