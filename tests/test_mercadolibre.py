import unittest
from unittest.mock import Mock, patch

from scrappers.mercadolibre import (
    fetch_api_results,
    parse_products_api,
    refresh_access_token,
    scrape_search,
)


class MercadoLibreScraperTests(unittest.TestCase):
    def test_parse_products_api_normalizes_results(self):
        products = parse_products_api([
            {
                "title": "Placa De Video RTX 3060 Ti",
                "price": 550000,
                "currency_id": "ARS",
                "permalink": "https://articulo.mercadolibre.com.ar/MLA-test",
            },
            {
                "title": "Producto incompleto",
                "price": None,
                "currency_id": "ARS",
                "permalink": "https://articulo.mercadolibre.com.ar/MLA-bad",
            },
        ])

        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]["store"], "mercadolibre")
        self.assertEqual(products[0]["name"], "Placa De Video RTX 3060 Ti")
        self.assertEqual(products[0]["price"], 550000)
        self.assertEqual(products[0]["currency"], "ARS")
        self.assertEqual(
            products[0]["url"],
            "https://articulo.mercadolibre.com.ar/MLA-test",
        )

    @patch("scrappers.mercadolibre.requests.get")
    def test_fetch_api_results_returns_empty_when_api_forbids_public_access(self, mock_get):
        response = Mock(status_code=403)
        mock_get.return_value = response

        self.assertEqual(fetch_api_results("rtx 3060 ti"), [])

    @patch.dict(
        "os.environ",
        {
            "REFRESH_TOKEN": "refresh-token",
            "APP_ID": "app-id",
            "CLIENT_SECRET": "client-secret",
        },
        clear=True,
    )
    @patch("scrappers.mercadolibre.requests.post")
    def test_refresh_access_token_accepts_existing_env_names(self, mock_post):
        response = Mock()
        response.json.return_value = {"access_token": "new-access-token"}
        response.raise_for_status.return_value = None
        mock_post.return_value = response

        token = refresh_access_token()

        self.assertEqual(token, "new-access-token")
        payload = mock_post.call_args.kwargs["data"]
        self.assertEqual(payload["client_id"], "app-id")
        self.assertEqual(payload["client_secret"], "client-secret")
        self.assertEqual(payload["refresh_token"], "refresh-token")

    @patch("scrappers.mercadolibre.fetch_html")
    @patch("scrappers.mercadolibre.fetch_api_results")
    def test_scrape_search_uses_api_products_first(self, mock_api, mock_html):
        mock_api.return_value = [
            {
                "title": "Placa De Video RTX 3060 Ti",
                "price": 550000,
                "currency_id": "ARS",
                "permalink": "https://articulo.mercadolibre.com.ar/MLA-test",
            }
        ]

        products = scrape_search("rtx 3060 ti")

        self.assertEqual(len(products), 1)
        mock_html.assert_not_called()


if __name__ == "__main__":
    unittest.main()
