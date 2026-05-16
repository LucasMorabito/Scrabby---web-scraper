import unittest

from scrappers.mexx import parse_products as parse_mexx_products
from scrappers.quantumhardstore import parse_products as parse_quantum_products


class MexxScraperTests(unittest.TestCase):
    def test_parse_products_normalizes_price_and_absolute_url(self):
        html = """
        <div class="card-body">
          <h4 class="card-title">
            <a href="/productos-rubro/placas-de-video/test.html">
              Placa De Video RTX 4060
            </a>
          </h4>
          <div class="price">
            <h4><b>$1.234.567,89</b></h4>
          </div>
        </div>
        """

        products = parse_mexx_products(html)

        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]["store"], "mexx")
        self.assertEqual(products[0]["name"], "Placa De Video RTX 4060")
        self.assertEqual(products[0]["price"], 1234567.89)
        self.assertEqual(
            products[0]["url"],
            "https://www.mexx.com.ar/productos-rubro/placas-de-video/test.html",
        )

    def test_parse_products_filters_accessories(self):
        html = """
        <div class="card-body">
          <h4 class="card-title">
            <a href="/cable.html">Cable Adaptador HDMI</a>
          </h4>
          <div class="price">
            <h4><b>$999.999</b></h4>
          </div>
        </div>
        """

        self.assertEqual(parse_mexx_products(html), [])


class QuantumHardstoreScraperTests(unittest.TestCase):
    def test_parse_products_reads_variants_from_article_and_uses_discount_price(self):
        html = """
        <article
          class="js-item-product"
          data-variants='[
            {
              "price_number": 893077.83,
              "price_with_payment_discount_short": "$580.500,59",
              "available": true,
              "stock": 7
            }
          ]'
        >
          <a
            class="js-product-item-image-link-private"
            href="/productos/placa-test/"
            title="PLACA DE VIDEO RX 7600"
          ></a>
        </article>
        """

        products = parse_quantum_products(html)

        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]["store"], "quantum")
        self.assertEqual(products[0]["name"], "PLACA DE VIDEO RX 7600")
        self.assertEqual(products[0]["price"], 580500.59)
        self.assertEqual(
            products[0]["url"],
            "https://quantumhardstore.com/productos/placa-test/",
        )

    def test_parse_products_skips_unavailable_variants(self):
        html = """
        <article
          class="js-item-product"
          data-variants='[
            {
              "price_number": 500000,
              "available": false,
              "stock": 0
            }
          ]'
        >
          <a
            class="js-product-item-image-link-private"
            href="/productos/sin-stock/"
            title="PLACA DE VIDEO SIN STOCK"
          ></a>
        </article>
        """

        self.assertEqual(parse_quantum_products(html), [])


if __name__ == "__main__":
    unittest.main()
