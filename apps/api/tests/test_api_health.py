import unittest

from movie_night_mediator.api.main import create_app


class ApiHealthTest(unittest.TestCase):
    def test_health_route_is_registered(self) -> None:
        app = create_app()

        paths = {route.path for route in app.routes}

        self.assertIn("/health", paths)

    def test_openapi_contract_includes_health_route(self) -> None:
        app = create_app()
        schema = app.openapi()

        self.assertEqual(schema["info"]["title"], "Movie Night Mediator API")
        self.assertIn("/health", schema["paths"])


if __name__ == "__main__":
    unittest.main()
