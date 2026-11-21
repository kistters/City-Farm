"""Identidade casual dos jogadores; não é autenticação."""
import re

PLAYER_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")


def normalize_player(player_id, nickname):
    if not isinstance(player_id, str) or not PLAYER_ID_PATTERN.fullmatch(player_id):
        raise ValueError("Invalid player ID")
    if not isinstance(nickname, str):
        raise ValueError("Invalid nickname")
    nickname = nickname.strip()
    if not 1 <= len(nickname) <= 24 or any(
        not (char.isalnum() or char in " _-") for char in nickname
    ):
        raise ValueError("Nickname must contain 1–24 letters, digits, spaces, _ or -")
    return {"id": player_id, "name": nickname}
