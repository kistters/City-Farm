"""Static regression checks for the standalone role pages.

Run from the repository root:
    python -m unittest discover -s tests -p 'test_role_pages.py'
No Docker, JavaScript runtime or browser required.
"""
from html.parser import HTMLParser
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
FRONT = ROOT / "CityFarm" / "front"


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.links = []
        self.scripts = []
        self.viewport = False

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if "id" in values:
            self.ids.append(values["id"])
        if tag == "a" and "href" in values:
            self.links.append(values["href"])
        if tag == "script" and "src" in values:
            self.scripts.append(values["src"].split("?")[0])
        if tag == "meta" and values.get("name") == "viewport":
            self.viewport = True


def parse(filename):
    parser = PageParser()
    parser.feed((FRONT / filename).read_text(encoding="utf-8"))
    return parser


class RolePageTests(unittest.TestCase):
    def test_role_selection_and_routes(self):
        home = parse("index.html")
        self.assertTrue(home.viewport)
        self.assertIn("/farmer", home.links)
        self.assertIn("/citizen", home.links)
        self.assertIn("/dashboard", home.links)
        self.assertNotIn("/js/farmer.js", home.scripts)
        self.assertNotIn("/js/citizen.js", home.scripts)

    def test_vue_components_are_scoped_by_page(self):
        farmer = parse("farmer.html")
        citizen = parse("citizen.html")
        dashboard = parse("dashboard.html")

        self.assertIn("farmer", farmer.ids)
        self.assertIn("dashboard", farmer.ids)
        self.assertNotIn("citizen", farmer.ids)
        self.assertIn("/js/farmer.js", farmer.scripts)
        self.assertIn("/js/dashboard.js", farmer.scripts)
        self.assertNotIn("/js/citizen.js", farmer.scripts)

        self.assertIn("citizen", citizen.ids)
        self.assertNotIn("farmer", citizen.ids)
        self.assertNotIn("dashboard", citizen.ids)
        self.assertIn("/js/citizen.js", citizen.scripts)
        self.assertNotIn("/js/farmer.js", citizen.scripts)

        self.assertIn("dashboard", dashboard.ids)
        self.assertNotIn("farmer", dashboard.ids)
        self.assertIn("/js/dashboard.js", dashboard.scripts)

        for page in (farmer, citizen, dashboard):
            self.assertTrue(page.viewport)
            self.assertEqual(len(page.ids), len(set(page.ids)))

    def test_nginx_routes_and_responsive_css(self):
        nginx = (ROOT / "nginx/conf.d/city-farm.conf").read_text()
        css = (FRONT / "css/dashboard.css").read_text()
        for route in ("/farmer", "/citizen"):
            self.assertIn("location = " + route, nginx)
        for breakpoint in ("850px", "600px"):
            self.assertIn(breakpoint, css)
        self.assertIn("min-height: 44px", css)
        self.assertIn(".role-cards", css)
        self.assertIn(".product-grid", css)


if __name__ == "__main__":
    unittest.main()
