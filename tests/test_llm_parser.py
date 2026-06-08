import unittest
from unittest.mock import patch, MagicMock
from scrappers.llm_parser import llm_parse_products

class TestLLMFallback(unittest.TestCase):
    
    @patch('scrappers.llm_parser.genai.Client')
    def test_llm_fallback_success(self, mock_genai_client):
        # 1. Configuramos el "simulador" de la IA para que devuelva un JSON estricto
        mock_response = MagicMock()
        mock_response.text = '[{"name": "ASUS RTX 4060 8GB", "price": 1289999.0, "url": "/producto/rtx-4060-asus"}]'
        
        mock_instance = mock_genai_client.return_value
        mock_instance.models.generate_content.return_value = mock_response

        # 2. HTML ficticio y sucio
        html_falso = "<html><body><p>ASUS RTX 4060 8GB cuesta $1.289.999</p></body></html>"
        
        # 3. Ejecutamos la función a testear
        resultados = llm_parse_products(html_falso, store="mexx", base_url="https://www.mexx.com.ar")
        
        # 4. Validamos que el LLM armó el esquema perfecto y resolvió la URL
        self.assertEqual(len(resultados), 1)
        self.assertEqual(resultados[0]["name"], "ASUS RTX 4060 8GB")
        self.assertEqual(resultados[0]["price"], 1289999.0)
        self.assertEqual(resultados[0]["url"], "https://www.mexx.com.ar/producto/rtx-4060-asus")
        self.assertEqual(resultados[0]["store"], "mexx")

    @patch('scrappers.llm_parser.genai.Client')
    def test_llm_fallback_invalid_json(self, mock_genai_client):
        # Simulamos que la IA alucina y devuelve texto en lugar de JSON
        mock_response = MagicMock()
        mock_response.text = "Hola, no pude encontrar ningún producto aquí."
        
        mock_instance = mock_genai_client.return_value
        mock_instance.models.generate_content.return_value = mock_response

        resultados = llm_parse_products("<html></html>", store="mexx")
        
        # Debe manejar el error silenciosamente y devolver lista vacía para no romper el scraper
        self.assertEqual(resultados, [])