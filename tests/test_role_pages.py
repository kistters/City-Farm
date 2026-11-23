"""Static regression checks for the standalone role pages.

Run from the repository root:
    python -m unittest discover -s tests -p 'test_role_pages.py'
No Docker, JavaScript runtime or browser required.
"""
from html.parser import HTMLParser
from pathlib import Path
import unittest

ROOT = Path("/workspace")
if not ROOT.is_dir():
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
        self.assertNotIn("dashboard", farmer.ids)
        self.assertNotIn("citizen", farmer.ids)
        self.assertIn("/js/farmer.js", farmer.scripts)
        self.assertNotIn("/js/dashboard.js", farmer.scripts)
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

    def test_citizen_work_levels_have_career_names(self):
        html = (FRONT / "citizen.html").read_text(encoding="utf-8")
        script = (FRONT / "js/citizen.js").read_text(encoding="utf-8")
        for name in ("Intern", "Employee", "Consultant"):
            self.assertIn(name, script)
        self.assertIn("levelNames[option]", html)
        self.assertIn("levelNames[challenge.level]", html)
        self.assertIn("level: this.level", script)

    def test_farmer_no_longer_requires_plots(self):
        html = (FRONT / "farmer.html").read_text(encoding="utf-8")
        script = (FRONT / "js/farmer.js").read_text(encoding="utf-8")
        websocket = (ROOT / "CityFarm/code/websocket.py").read_text(
            encoding="utf-8")
        for source in (html, script):
            self.assertNotIn("plot", source.lower())
        self.assertIn("soil_health", html)
        self.assertIn("soilCosts", script)
        self.assertNotIn('plot=request.get("plot")', websocket)

    def test_farmer_multiculture_selection_and_challenge_actions(self):
        html = (FRONT / "farmer.html").read_text(encoding="utf-8")
        script = (FRONT / "js/farmer.js").read_text(encoding="utf-8")
        self.assertNotIn("selectedProduct", html)
        self.assertNotIn("selectedProduct", script)
        self.assertIn("Every successful planting", html)
        self.assertIn("v-bind:class=\"'sprite-'+cell\"", html)
        self.assertIn("sprite-farm-", html)
        self.assertIn("sprite-soil-hoe", html)
        self.assertIn("sprite-soil-tractor", html)
        self.assertIn("this.challenge.symbol", script)
        self.assertIn("v-on:click=\"reviewPattern\"", html)
        self.assertIn("v-on:click=\"cancelChallenge\"", html)
        self.assertIn("beginObservation: function", script)
        self.assertIn("farm_cancel:", script)
        self.assertIn("self.answer = Array(", script)

    def test_single_food_item_in_market(self):
        farmer = (FRONT / "farmer.html").read_text(encoding="utf-8")
        citizen = (FRONT / "citizen.html").read_text(encoding="utf-8")
        dashboard = (FRONT / "dashboard.html").read_text(encoding="utf-8")
        citizen_js = (FRONT / "js/citizen.js").read_text(encoding="utf-8")
        for html in (farmer, citizen, dashboard):
            self.assertNotIn("productCatalog", html)
        self.assertNotIn("market.food", farmer)
        self.assertIn("market.food", citizen)
        self.assertIn("market.food", dashboard)
        self.assertIn("buy_food: true", citizen_js)
        self.assertNotIn("buy_food: product", citizen_js)

    def test_shared_pixel_art_assets_and_citizen_layout(self):
        import struct

        sprite = FRONT / "css/images/pixel-cityfarm.png"
        data = sprite.read_bytes()
        self.assertEqual(data[:8], bytes.fromhex("89504e470d0a1a0a"))
        self.assertEqual(struct.unpack(">II", data[16:24]), (200, 120))

        css = (FRONT / "css/dashboard.css").read_text(encoding="utf-8")
        farmer = (FRONT / "farmer.html").read_text(encoding="utf-8")
        citizen = (FRONT / "citizen.html").read_text(encoding="utf-8")
        home = (FRONT / "index.html").read_text(encoding="utf-8")
        dashboard = (FRONT / "dashboard.html").read_text(encoding="utf-8")
        for icon in (
            "soil-hoe", "soil-tractor", "farm-1", "farm-2", "farm-3",
            "citizen-rest", "food", "career-1", "career-2", "career-3",
            "corn", "wheat", "carrot", "lettuce", "tomato",
        ):
            self.assertIn(".sprite-" + icon, css)
        for html in (farmer, citizen, home, dashboard):
            self.assertIn("pixel-sprite", html)
        self.assertIn("image-rendering:pixelated", css)
        self.assertIn("sprite-career-", citizen)
        self.assertIn("sprite-citizen-rest", citizen)
        self.assertIn("sprite-food", citizen)
        self.assertIn("v-on:click=\"buyFood\"", citizen)
        self.assertNotIn("Buy and eat", citizen)
        self.assertIn("resource-actions", farmer)
        self.assertIn("resource-actions", citizen)

    def test_dashboard_market_character_counters_and_resource_symmetry(self):
        farmer = (FRONT / "farmer.html").read_text(encoding="utf-8")
        citizen = (FRONT / "citizen.html").read_text(encoding="utf-8")
        dashboard = (FRONT / "dashboard.html").read_text(encoding="utf-8")
        dashboard_js = (FRONT / "js/dashboard.js").read_text(encoding="utf-8")
        farmer_js = (FRONT / "js/farmer.js").read_text(encoding="utf-8")
        citizen_js = (FRONT / "js/citizen.js").read_text(encoding="utf-8")
        websocket = (ROOT / "CityFarm/code/websocket.py").read_text(
            encoding="utf-8")
        css = (FRONT / "css/dashboard.css").read_text(encoding="utf-8")

        self.assertNotIn("Food available", farmer)
        self.assertNotIn("market.food", farmer)
        self.assertIn("Food available", dashboard)
        self.assertIn("Food supplied by all Farmers", dashboard)
        for field in ("food_produced", "food_eaten", "coins_earned_work",
                      "coins_spent_soil"):
            self.assertIn("character." + field, dashboard)
        self.assertIn("characters: []", dashboard_js)
        self.assertIn('if (data.characters)', dashboard_js)
        self.assertIn("register_player_character(", websocket)
        self.assertIn("dashboard_update()", websocket)

        for html in (farmer, citizen):
            self.assertIn('class="resource-health"', html)
            self.assertIn('class="section-head compact"', html)
            self.assertIn('class="resource-actions"', html)
        self.assertIn("<h3>Soil Health</h3>", farmer)
        self.assertIn("<h3>Energy</h3>", citizen)
        self.assertIn(".resource-health", css)
        self.assertNotIn("soil-health", css)
        self.assertIn("profile.role = 'farmer'", farmer_js)
        self.assertIn("profile.role = 'citizen'", citizen_js)

    def test_english_ui_and_pixel_art_coins(self):
        coin = FRONT / "css/images/pixel-coin.svg"
        self.assertTrue(coin.is_file())
        asset = coin.read_text(encoding="utf-8")
        self.assertIn("<svg", asset)
        self.assertIn('shape-rendering="crispEdges"', asset)
        css = (FRONT / "css/dashboard.css").read_text(encoding="utf-8")
        self.assertIn(".coin-icon", css)
        self.assertIn("image-rendering:pixelated", css)
        for name in ("farmer.html", "citizen.html"):
            page = (FRONT / name).read_text(encoding="utf-8")
            self.assertIn('class="coin-balance"', page)
            self.assertIn('src="/css/images/pixel-coin.svg"', page)
            self.assertIn('alt="Coins"', page)
            self.assertNotIn("Coins <strong>", page)
        for name in ("farmer.html", "citizen.html", "dashboard.html",
                     "js/farmer.js", "js/citizen.js"):
            text = (FRONT / name).read_text(encoding="utf-8")
            for phrase in ("Saúde do Solo", "Grátis", "moedas", "Energia",
                           "Descansar", "Comer Food", "Personagens", "Personagem",
                           "Estagiário", "Efetivo", "Consultor", "Multicultura",
                           "Ver padrão novamente", "Cancelar desafio"):
                self.assertNotIn(phrase, text, msg=name)
        farmer = (FRONT / "js/farmer.js").read_text(encoding="utf-8")
        citizen = (FRONT / "js/citizen.js").read_text(encoding="utf-8")
        for label in ("Family Monoculture", "Large-Scale Monoculture", "Polyculture"):
            self.assertIn(label, farmer)
        for label in ("Intern", "Employee", "Consultant"):
            self.assertIn(label, citizen)

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
