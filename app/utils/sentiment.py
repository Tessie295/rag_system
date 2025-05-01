import re
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from typing import Dict, Any

# Descargar recursos necesarios para NLTK
try:
    nltk.download("vader_lexicon", quiet=True)
except:
    pass  # Manejar escenarios offline


class SentimentAnalyzer:
    """Analizador de sentimiento para adaptar el tono de las respuestas."""

    def __init__(self):
        """Inicializar el analizador de sentimiento."""
        self.analyzer = SentimentIntensityAnalyzer()

    def analyze(self, text: str) -> Dict[str, Any]:
        """
        Analizar el sentimiento de un texto.

        Args:
            text: Texto a analizar

        Returns:
            Dict con scores de sentimiento y clasificación
        """
        # Análisis de sentimiento usando VADER
        sentiment_scores = self.analyzer.polarity_scores(text)

        # Determinar clasificación
        compound_score = sentiment_scores["compound"]

        if compound_score >= 0.05:
            sentiment = "positive"
        elif compound_score <= -0.05:
            sentiment = "negative"
        else:
            sentiment = "neutral"

        # Detectar urgencia o frustración
        urgent_patterns = [
            r"\burgen(t|cy)\b",
            r"\bASAP\b",
            r"\bimmediately\b",
            r"\bquick(ly)?\b",
            r"\bfast\b",
            r"\bas soon as\b",
        ]

        frustrated_patterns = [
            r"\bfrustrat(ed|ing)\b",
            r"\bupset\b",
            r"\bangry\b",
            r"\birrita(ted|ting)\b",
            r"\bannoy(ed|ing)\b",
            r"\bnot working\b",
            r"\bcan\'?t\b.{1,30}\bwork\b",
            r"\bwhy\b.{1,10}\bnot\b.{1,20}\bwork(ing)?\b",
            r"\bfail(ed|ure|ing)\b",
            r"\berror\b",
            r"\bissue\b",
            r"\bproblem\b",
        ]

        is_urgent = any(
            re.search(pattern, text, re.IGNORECASE) for pattern in urgent_patterns
        )
        is_frustrated = any(
            re.search(pattern, text, re.IGNORECASE) for pattern in frustrated_patterns
        )

        return {
            "scores": sentiment_scores,
            "sentiment": sentiment,
            "is_urgent": is_urgent,
            "is_frustrated": is_frustrated,
        }

    def get_response_tone(self, sentiment_data: Dict[str, Any]) -> str:
        """
        Determinar el tono apropiado para la respuesta basado en el análisis de sentimiento.

        Args:
            sentiment_data: Resultado del análisis de sentimiento

        Returns:
            Tono recomendado: "supportive", "professional", "enthusiastic", o "empathetic"
        """
        if sentiment_data["is_frustrated"]:
            return "empathetic"
        elif sentiment_data["is_urgent"]:
            return "professional"
        elif sentiment_data["sentiment"] == "positive":
            return "enthusiastic"
        elif sentiment_data["sentiment"] == "negative":
            return "supportive"
        else:
            return "professional"
