import hashlib
import json
import unittest
from unittest.mock import patch

from products import PRODUCT_DIFFICULTIES
from tasks import valid_proof, verify_product_proof, record_proof


class ProofOfWorkTests(unittest.TestCase):
    farmer = {"id": "b" * 32, "name": "farmer"}

    def solve(self, challenge, difficulty):
        return next(
            nonce for nonce in range(1000000)
            if hashlib.sha256(f"{challenge}:{nonce}".encode()).hexdigest().startswith("0" * difficulty)
        )

    def test_catalog_covers_existing_products(self):
        self.assertEqual(
            set(PRODUCT_DIFFICULTIES),
            {"corn", "wheat", "celery", "carrot", "lettuce", "tomato"},
        )

    def test_valid_proof(self):
        challenge = "cityfarm:v1:abc:tomato:token"
        nonce = self.solve(challenge, 3)
        self.assertTrue(valid_proof(challenge, nonce, 3))
        self.assertFalse(valid_proof(challenge, nonce, 65))

    def test_each_product_can_be_verified(self):
        for product, difficulty in PRODUCT_DIFFICULTIES.items():
            with self.subTest(product=product):
                identifier = "a" * 32
                challenge = f"cityfarm:v1:{identifier}:{product}:token"
                nonce = self.solve(challenge, difficulty)
                payload = json.dumps({"challenge": challenge, "product": product, "difficulty": difficulty, "farmer": self.farmer})
                with patch("tasks.r") as redis_mock, patch("tasks.ACCEPT_PROOF") as accept, patch("tasks.notify"):
                    redis_mock.get.return_value = payload.encode()
                    accept.return_value = 1
                    self.assertTrue(verify_product_proof.run(identifier, nonce, self.farmer))
                    keys = accept.call_args.kwargs["keys"]
                    self.assertEqual(keys[1], "products:" + product)
                    self.assertEqual(keys[2], product)

    def test_replay_is_rejected(self):
        product = "tomato"
        identifier = "a" * 32
        challenge = f"cityfarm:v1:{identifier}:{product}:token"
        payload = json.dumps({"challenge":challenge,"product":product,"difficulty":3,"farmer":self.farmer})
        nonce = self.solve(challenge, 3)
        with patch("tasks.r") as redis_mock, patch("tasks.ACCEPT_PROOF") as accept, patch("tasks.notify"):
            redis_mock.get.return_value = payload.encode()
            accept.side_effect = [1, 0]
            self.assertTrue(verify_product_proof.run(identifier, nonce, "farmer"))
            self.assertFalse(verify_product_proof.run(identifier, nonce, "farmer"))

    def test_server_difficulty_cannot_be_downgraded(self):
        identifier = "a" * 32
        challenge = f"cityfarm:v1:{identifier}:wheat:token"
        payload = json.dumps({"challenge":challenge,"product":"wheat","difficulty":2,"farmer":self.farmer})
        with patch("tasks.r") as redis_mock, patch("tasks.ACCEPT_PROOF") as accept, patch("tasks.notify"):
            redis_mock.get.return_value = payload.encode()
            self.assertFalse(verify_product_proof.run(identifier, 1, self.farmer))
            accept.assert_not_called()

    def test_missing_challenge_rejected(self):
        with patch("tasks.r") as redis_mock, patch("tasks.notify"):
            redis_mock.get.return_value = None
            self.assertFalse(verify_product_proof.run("a"*32, 1, self.farmer))

    def test_history_records_product(self):
        with patch("tasks.r") as redis_mock, patch("tasks.notify"):
            record_proof("a"*32, 4, self.farmer, "000abc", True, "accepted", "corn")
            event = json.loads(redis_mock.pipeline.return_value.lpush.call_args.args[1])
            self.assertEqual(event["product"], "corn")
            self.assertEqual(event["farmer_id"], self.farmer["id"])
            self.assertTrue(event["valid"])
