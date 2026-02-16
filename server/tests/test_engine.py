import unittest
import pandas as pd
import sys
import os
from unittest.mock import MagicMock, patch

# Añadir el path para importar los módulos del motor
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.engine import bi_analyst, executor, prompts

class TestBIEngine(unittest.TestCase):

    def setUp(self):
        # Crear un DataFrame de prueba
        self.df = pd.DataFrame({
            'producto': ['A', 'B', 'A', 'C'],
            'ventas': [100, 200, 150, 300]
        })

    def test_executor_separation(self):
        """Prueba que el executor pueda separar narrativa de código correctamente."""
        raw_response = "Aquí tienes el análisis:\n```python\nfig = px.bar(df, x='producto', y='ventas')\nprint('Total: 750')\n```"
        narrative, fig = executor.execute_analysis(self.df, raw_response, "df")
        
        self.assertIn("Aquí tienes el análisis", narrative)
        self.assertIn("Total: 750", narrative)
        self.assertIsNotNone(fig)

    def test_prompts_templates(self):
        """Prueba que las plantillas de prompts se formateen correctamente."""
        context = "Columns: [a, b]"
        query = "Test query"
        formatted = prompts.ENGINEER_PROMPT_TEMPLATE.format(
            data_var="df",
            query=query,
            context_str=context
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

    @patch('src.engine.bi_analyst.generate_ai_content')
    def test_analyze_data_flow(self, mock_ai):
        """Prueba el flujo de analyze_data (simulando la IA)."""
        mock_ai.side_effect = [
            "```python\nprint('Resultado: 10')\nfig = px.pie(df, names='producto')\n```", 
            "Informe estratégico basado en los datos." 
        ]
        
        result = bi_analyst.analyze_data(self.df, "Test query", "fake_key")
        
        self.assertIn("Informe estratégico", result)
        self.assertIn("```python", result)
        self.assertEqual(mock_ai.call_count, 2)

    def test_security_sandbox_attack(self):
        """Prueba que el sandbox bloquee intentos de acceso al sistema."""
        # Intento de importar OS (Debe fallar porque __import__ no está)
        attack_code = "```python\nimport os\nos.system('echo hack')\n```"
        narrative, fig = executor.execute_analysis(self.df, attack_code, "df")
        self.assertIn("Bloqueo de Seguridad", narrative)
        
        # Intento de usar open() (Debe fallar porque no está en builtins y está en el bloqueador)
        attack_code_2 = "```python\nf = open('test.txt', 'w')\n```"
        narrative, fig = executor.execute_analysis(self.df, attack_code_2, "df")
        self.assertIn("Bloqueo de Seguridad", narrative)

if __name__ == '__main__':
    unittest.main()
