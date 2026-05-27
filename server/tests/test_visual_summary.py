import unittest
import sys
import os
import json
from unittest.mock import MagicMock, patch

# Añadir el path para importar los módulos
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.engine.visual_summary_engine import (
    validate_visual_summary_response,
    generate_visual_summary,
    VALID_VISUAL_TYPES
)

class TestVisualSummary(unittest.TestCase):

    def setUp(self):
        # Datos de prueba de una respuesta JSON válida
        self.valid_response_data = {
            "title": "Proceso de Venta Semanal",
            "summary": ["El volumen de ventas aumentó 15%", "El producto A lidera el mercado"],
            "key_points": ["Lunes se registró el pico máximo", "Producto C requiere reabastecimiento"],
            "visual_type": "flowchart",
            "mermaid": "graph TD\nA[Lunes] --> B[Venta Alta]",
            "confidence": "high"
        }

    def test_validation_success(self):
        """Prueba que un diccionario válido pase sin problemas la validación."""
        validated = validate_visual_summary_response(self.valid_response_data)
        self.assertEqual(validated["title"], "Proceso de Venta Semanal")
        self.assertEqual(validated["visual_type"], "flowchart")
        self.assertEqual(validated["confidence"], "high")

    def test_validation_invalid_type(self):
        """Prueba que un tipo visual no permitido arroje un ValueError."""
        invalid_data = self.valid_response_data.copy()
        invalid_data["visual_type"] = "grafico_circular" # No permitido
        with self.assertRaises(ValueError) as ctx:
            validate_visual_summary_response(invalid_data)
        self.assertIn("visual_type", str(ctx.exception))

    def test_validation_missing_fields(self):
        """Prueba que falte un campo obligatorio (como title) arroje ValueError."""
        invalid_data = self.valid_response_data.copy()
        del invalid_data["title"]
        with self.assertRaises(ValueError) as ctx:
            validate_visual_summary_response(invalid_data)
        self.assertIn("title", str(ctx.exception))

    def test_validation_invalid_summary_type(self):
        """Prueba que summary no sea un array de strings arroje ValueError."""
        invalid_data = self.valid_response_data.copy()
        invalid_data["summary"] = "No soy un array"
        with self.assertRaises(ValueError) as ctx:
            validate_visual_summary_response(invalid_data)
        self.assertIn("summary", str(ctx.exception))

    @patch('src.engine.visual_summary_engine.get_client')
    def test_generate_visual_summary_quick_mode(self, mock_get_client):
        """Prueba el flujo del modo rápido simulando el cliente de Gemini."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        # Respuesta del LLM simulado en formato string de JSON
        mock_response.text = json.dumps(self.valid_response_data)
        mock_client.models.generate_content.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = generate_visual_summary(
            text="Texto de prueba de ventas del lunes y producto A",
            provider="gemini",
            api_key="fake_gemini_api_key_valid",
            mode="rapido"
        )

        self.assertEqual(result["title"], "Proceso de Venta Semanal")
        self.assertEqual(result["visual_type"], "flowchart")
        self.assertEqual(result["confidence"], "high")
        mock_client.models.generate_content.assert_called_once()

    @patch('src.engine.visual_summary_engine._generate_quick_mode')
    def test_generate_visual_summary_quality_fallback(self, mock_quick_mode):
        """Prueba que el modo calidad ejecute el fallback al modo rápido en Fase 1."""
        mock_quick_mode.return_value = self.valid_response_data
        
        result = generate_visual_summary(
            text="Texto largo para probar calidad",
            provider="gemini",
            api_key="fake_gemini_api_key_valid",
            mode="calidad"
        )
        
        self.assertEqual(result["title"], "Proceso de Venta Semanal")
        mock_quick_mode.assert_called_once()

    def test_generate_visual_summary_empty_text(self):
        """Prueba que pasar un texto vacío lance ValueError."""
        with self.assertRaises(ValueError) as ctx:
            generate_visual_summary(
                text="   ",
                provider="gemini",
                api_key="fake_key"
            )
        self.assertIn("vacío", str(ctx.exception))

if __name__ == '__main__':
    unittest.main()
