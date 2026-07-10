import os
import sys
from dotenv import load_dotenv

PROJECT_ROOT = "/Users/anurag/Projects/startup-intelligence"
sys.path.insert(0, PROJECT_ROOT)
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

# Ensure Ollama environment is set
os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"
os.environ["OLLAMA_MODEL"] = "qwen2.5:3b"

from backend.services.supabase_service import supabase
from backend.pipeline.news_processor import NewsProcessor

def cleanup_news_summaries():
    print("🔍 Fetching all news articles from database...")
    res = supabase.table("news_articles").select("id, headline, summary, content").execute()
    articles = res.data or []
    
    if not articles:
        print("No articles found in the registry.")
        return
        
    processor = NewsProcessor()
    updated_count = 0
    
    print(f"Total articles fetched: {len(articles)}")
    for art in articles:
        art_id = art["id"]
        headline = art["headline"]
        summary = art["summary"] or ""
        content = art["content"] or ""
        
        # If the summary does not contain the signature 'ICICI' prefix, it is a legacy raw RSS description.
        if "ICICI" not in summary:
            print(f"\n📝 Article '{headline[:40]}...' has raw legacy description. Regenerating short AI summary...")
            text_body = content if content else summary
            
            # Generate new short summary
            new_summary = processor.generate_ai_summary(headline, text_body)
            new_words = new_summary.split()
            print(f"✅ Generated new summary ({len(new_words)} words). Writing to database...")
            
            try:
                supabase.table("news_articles").update({"summary": new_summary}).eq("id", art_id).execute()
                updated_count += 1
            except Exception as e:
                print(f"❌ Failed to update article {art_id}: {e}")
                
    print(f"\n✨ Cleanup completed successfully! Regenerated and updated {updated_count} legacy summaries.")

if __name__ == "__main__":
    cleanup_news_summaries()
