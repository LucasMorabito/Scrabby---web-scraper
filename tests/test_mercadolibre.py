import unittest
from unittest.mock import Mock, patch

from scrappers.mercadolibre import fetch_html, parse_products_ld_json, scrape_search


SEARCH_HTML = """
<html>
  <head>
    <script type="application/ld+json">
      {
        "@context": "https://schema.org",
        "@graph": [
          {
            "@type": "Product",
            "name": "Placa De Video RTX 3060 Ti",
            "offers": {
              "price": 550000,
              "priceCurrency": "ARS",
              "url": "https://articulo.mercadolibre.com.ar/MLA-test"
            }
          },
          {
            "@type": "BreadcrumbList",
            "name": "Ignored"
          }
        ]
      }
    </script>
  </head>
</html>
"""


class MercadoLibreScraperTests(unittest.TestCase):
    def test_parse_products_ld_json_normalizes_products(self):
        products = parse_products_ld_json(SEARCH_HTML)

        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]["store"], "mercadolibre")
        self.assertEqual(products[0]["name"], "Placa De Video RTX 3060 Ti")
        self.assertEqual(products[0]["price"], 550000)
        self.assertEqual(products[0]["currency"], "ARS")
        self.assertEqual(
            products[0]["url"],
            "https://articulo.mercadolibre.com.ar/MLA-test",
        )

    @patch("scrappers.mercadolibre.llm_parse_products")
    def test_parse_products_ld_json_ignores_invalid_json(self, mock_llm):
        html = """
        <script type="application/ld+json">
          {"@graph":
        </script>
        """

        mock_llm.return_value = []
        self.assertEqual(parse_products_ld_json(html), [])

    @patch("scrappers.mercadolibre.HTTP_CLIENT.get")
    def test_fetch_html_uses_manual_search_headers_without_authorization(self, mock_get):
        response = Mock()
        response.text = SEARCH_HTML
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        html = fetch_html("https://listado.mercadolibre.com.ar/rtx-3060-ti")

        self.assertEqual(html, SEARCH_HTML)
        headers = mock_get.call_args.kwargs["headers"]
        from scrappers.mercadolibre import HTTP_CLIENT

        self.assertIn("User-Agent", HTTP_CLIENT.session.headers)
        self.assertEqual(headers["Accept"], "text/html")
        self.assertNotIn("Authorization", headers)

    @patch("scrappers.mercadolibre.fetch_html", return_value=SEARCH_HTML)
    def test_scrape_search_uses_manual_search_page(self, mock_fetch_html):
        products = scrape_search("rtx 3060 ti")

        self.assertEqual(len(products), 1)
        mock_fetch_html.assert_called_once_with(
            "https://listado.mercadolibre.com.ar/rtx-3060-ti"
        )

    @patch("scrappers.mercadolibre.fetch_html")
    def test_scrape_search_respects_limit(self, mock_fetch_html):
        mock_fetch_html.return_value = """
        <script type="application/ld+json">
          {
            "@graph": [
              {
                "@type": "Product",
                "name": "A",
                "offers": {"price": 1, "priceCurrency": "ARS", "url": "https://a"}
              },
              {
                "@type": "Product",
                "name": "B",
                "offers": {"price": 2, "priceCurrency": "ARS", "url": "https://b"}
              }
            ]
          }
        </script>
        """

        products = scrape_search("rtx", limit=1)

        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]["name"], "A")


if __name__ == "__main__":
    unittest.main()
