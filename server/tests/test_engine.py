import unittest
import pandas as pd
import sys
import os
from unittest.mock import MagicMock, patch

# Añadir el path para importar los módulos del motor
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.engine import bi_analyst, executor, prompts

class TestBIEngine(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        # Crear un DataFrame de prueba
        self.df = pd.DataFrame({
            'producto': ['A', 'B', 'A', 'C'],
            'ventas': [100, 200, 150, 300]
        })

    async def test_executor_separation(self):
        """Prueba que el executor pueda separar narrativa de código correctamente."""
        raw_response = "Aquí tienes el análisis:\n```python\nfig = px.bar(df, x='producto', y='ventas')\nprint('Total: 750')\n```"
        narrative, fig = await executor.execute_analysis(self.df, raw_response, "df")
        
        self.assertIn("Aquí tienes el análisis", narrative)
        self.assertIn("Total: 750", narrative)
        self.assertIsNotNone(fig)

    def test_prompts_templates(self):
        """Prueba que las plantillas de prompts se formateen correctamente."""
        formatted = prompts.EXECUTOR_PROMPT_TEMPLATE.format(
            query="Test query",
            plan="Test plan",
            data_info="Columns: [a, b]",
            muestra_datos="{}",
            table_names_hint="hint",
            data_var="df"
        )
        self.assertIn("Test query", formatted)
        self.assertIn("df", formatted)

    def test_safe_exec_cleaning(self):
        """Prueba el ejecutor de limpieza con una operación simple."""
        code = "```python\ndf['producto'] = df['producto'].str.lower()\nclean_summary = 'Convertido a minúsculas'\n```"
        # Extraer el código del bloque
        import re
        code_clean = re.search(r"```python\n(.*?)\n```", code, re.DOTALL).group(1)
        
        cleaned_df, summary = executor.safe_exec_cleaning(self.df, code_clean)
        
        self.assertEqual(cleaned_df['producto'].iloc[0], 'a')
        self.assertEqual(summary, 'Convertido a minúsculas')

    @patch('src.engine.bi_analyst.get_client')
    @patch('src.engine.bi_analyst.generate_ai_content')
    async def test_analyze_data_flow(self, mock_ai, mock_get_client):
        """Prueba el flujo de analyze_data (simulando la IA)."""
        # Mock para el cliente de Gemini y su validador
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '{"status": "success", "reason": "ok", "feedback": "none"}'
        mock_client.models.generate_content.return_value = mock_response
        mock_get_client.return_value = mock_client

        mock_ai.side_effect = [
            "Plan de análisis estratégico.",
            "```python\nprint('Resultado: 10')\nfig = px.pie(df, names='producto')\n```", 
            "Informe estratégico basado en los datos." 
        ]
        
        output_text, fig, raw_response = await bi_analyst.analyze_data(self.df, "Test query", "fake_key")
        
        self.assertIn("Informe estratégico", output_text)
        self.assertIn("```python", raw_response)
        self.assertEqual(mock_ai.call_count, 3)

    async def test_security_sandbox_attack(self):
        """Prueba que el sandbox bloquee intentos de acceso al sistema."""
        # Intento de importar OS (Debe fallar porque __import__ no está)
        attack_code = "```python\nimport os\nos.system('echo hack')\n```"
        narrative, fig = await executor.execute_analysis(self.df, attack_code, "df")
        self.assertTrue(any(x in narrative.lower() for x in ["seguridad", "restricción", "bloquea"]))
        
        # Intento de usar open() (Debe fallar porque no está en builtins y está en el bloqueador)
        attack_code_2 = "```python\nf = open('test.txt', 'w')\n```"
        narrative, fig = await executor.execute_analysis(self.df, attack_code_2, "df")
        self.assertTrue(any(x in narrative.lower() for x in ["seguridad", "restricción", "bloquea"]))

if __name__ == '__main__':
    unittest.main()
