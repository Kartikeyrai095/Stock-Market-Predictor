"""
Agent 6: News Intelligence
Fetches financial news via RSS or scraping.
Uses Hugging Face Transformers (FinBERT) to analyze sentiment.
"""

from agents.base_agent import BaseAgent
from config import NEWS_RSS_FEEDS
from utils.logger import get_logger
from database.db_manager import db
from database.models import SentimentRecord
import feedparser
from transformers import pipeline
import pandas as pd
from datetime import datetime

class NewsIntelligenceAgent(BaseAgent):
    def __init__(self):
        super().__init__("NewsIntelligence")
        self.session = None
        self.sentiment_analyzer = None

    def initialize(self) -> bool:
        try:
            self.session = db.get_session()
            self.logger.info("Loading FinBERT sentiment model (this may take a minute...)")
            # Using ProsusAI/finbert specifically trained on financial text
            self.sentiment_analyzer = pipeline("sentiment-analysis", model="ProsusAI/finbert")
            self.logger.info("FinBERT model loaded successfully.")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize FinBERT or DB: {e}")
            return False

    def execute(self, target_ticker=None, **kwargs) -> dict:
        """
        Scrape news and calculate sentiment.
        If target_ticker is None, gathers general market news.
        """
        if not self.sentiment_analyzer:
            if not self.initialize():
                return {"success": False, "error": "Analyzer not initialized"}

        self.logger.info("Starting News Intelligence collection")
        all_news = []
        
        # 1. Fetch from RSS Feeds
        for source_name, url in NEWS_RSS_FEEDS.items():
            try:
                self.logger.debug(f"Parsing feed: {source_name}")
                feed = feedparser.parse(url)
                
                # Take top 10 articles from each feed
                for entry in feed.entries[:10]:
                    title = entry.get('title', '')
                    summary = entry.get('summary', '')
                    text = f"{title}. {summary}"
                    
                    if len(text) > 20: 
                        all_news.append({
                            "source": source_name,
                            "headline": title[:500],
                            "text": text[:512] # Limit for BERT max seq length
                        })
            except Exception as e:
                self.logger.warning(f"Failed to parse {source_name}: {e}")

        if not all_news:
            return {"processed_articles": 0, "status": "No news found"}

        # 2. Analyze Sentiment
        results = []
        for i, news in enumerate(all_news):
            try:
                # Returns e.g. [{'label': 'positive', 'score': 0.85}]
                sentiment_result = self.sentiment_analyzer(news["text"])[0]
                
                label = sentiment_result['label'].upper() # POSITIVE, NEGATIVE, NEUTRAL
                score = float(sentiment_result['score'])
                
                # Convert to -1.0 to 1.0 scale
                num_score = 0.0
                if label == "POSITIVE":
                    num_score = score
                elif label == "NEGATIVE":
                    num_score = -score
                
                results.append({
                    "source": news["source"],
                    "headline": news["headline"],
                    "sentiment_score": num_score,
                    "sentiment_label": label,
                    "confidence": score
                })
            except Exception as e:
                self.logger.warning(f"Sentiment analysis failed for article {i}: {e}")

        # 3. Save to database
        try:
            records = [
                SentimentRecord(
                    ticker='MARKET',  # Currently tagging all generic RSS as MARKET
                    source=res["source"],
                    headline=res["headline"],
                    sentiment_score=res["sentiment_score"],
                    sentiment_label=res["sentiment_label"],
                    confidence=res["confidence"]
                ) for res in results
            ]
            self.session.bulk_save_objects(records)
            self.session.commit()
            self.logger.info(f"Saved {len(records)} sentiment records.")
        except Exception as e:
            self.logger.error(f"Failed to save sentiment to DB: {e}")
            self.session.rollback()

        # Calculate a daily aggregate sentiment for logging
        agg_score = sum([r["sentiment_score"] for r in results]) / len(results) if results else 0
        
        return {
            "processed_articles": len(results),
            "aggregate_market_score": round(agg_score, 3)
        }

    def __del__(self):
        if self.session:
            self.session.close()
