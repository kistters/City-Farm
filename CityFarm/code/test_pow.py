import hashlib
import unittest
from unittest.mock import patch

from tasks import valid_proof, verify_tomato_proof


class ProofOfWorkTests(unittest.TestCase):
    def test_valid_proof_uses_sha256(self):
        challenge = "cityfarm:v1:abc:tomato:xyz"
        nonce = next(
            n for n in range(200000)
            if hashlib.sha256(f"{challenge}:{n}".encode()).hexdigest().startswith("000")
        )
        self.assertTrue(valid_proof(challenge, nonce))
        self.assertFalse(valid_proof(challenge, nonce, difficulty=65))

    def test_invalid_or_missing_challenge_does_not_produce(self):
        with patch("tasks.r") as redis_mock, patch("tasks.ACCEPT_PROOF") as accept:
            redis_mock.get.return_value = None
            self.assertFalse(verify_tomato_proof.run("a" * 32, 0, "farmer"))
            accept.assert_not_called()

    def test_reused_proof_is_rejected_atomically(self):
        challenge_id = "a" * 32
        challenge = f"cityfarm:v1:{challenge_id}:tomato:token"
        nonce = next(
            n for n in range(200000)
            if hashlib.sha256(f"{challenge}:{n}".encode()).hexdigest().startswith("000")
        )
        with patch("tasks.r") as redis_mock, patch("tasks.ACCEPT_PROOF") as accept, patch("tasks.notify"):
            redis_mock.get.return_value = challenge.encode()
            accept.side_effect = [1, 0]
            self.assertTrue(verify_tomato_proof.run(challenge_id, nonce, "farmer"))
            self.assertFalse(verify_tomato_proof.run(challenge_id, nonce, "farmer"))
            self.assertEqual(accept.call_count, 2)

    def test_malformed_nonce_rejected(self):
        with patch("tasks.r") as redis_mock:
            self.assertFalse(verify_tomato_proof.run("a" * 32, True, "farmer"))
            redis_mock.get.assert_not_called()


if __name__ == "__main__":
    unittest.main()
