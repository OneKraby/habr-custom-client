import re
from datetime import datetime, timezone
from typing import List, Literal, Optional

import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException, Query, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app import models, database, scraper

# Create tables
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Habr Custom API")

# Dependency
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

class ArticleSchema(BaseModel):
    id: str
    title: str
    url: str
    date: str
    score: int
    is_active: bool

    class Config:
        from_attributes = True

def parse_habr_date(datetime_str: str) -> Optional[datetime]:
    if not datetime_str:
        return None
    if datetime_str.endswith('Z'):
        datetime_str = datetime_str[:-1] + '+00:00'
    try:
        return datetime.fromisoformat(datetime_str)
    except ValueError:
        return None

def extract_articles_from_html(html: str) -> List[dict]:
    soup = BeautifulSoup(html, 'html.parser')
    articles = soup.find_all('article')
    
    articles_data = []
    for art in articles:
        article_id = art.get('id')
        if not article_id:
            continue
            
        time_tag = art.find('time')
        if not time_tag or not time_tag.has_attr('datetime'):
            continue
            
        pub_date = parse_habr_date(time_tag['datetime'])
        if not pub_date:
            continue
            
        # Extract title
        title_tag = art.find('h2')
        title = title_tag.text.strip() if title_tag else "No Title"
        
        # Extract URL
        link_tag = art.find('a', class_='tm-title__link')
        if link_tag and link_tag.has_attr('href'):
            link = f"https://habr.com{link_tag['href']}"
        else:
            link = ""
            
        # Extract score (rating)
        score = 0
        score_tag = art.find(class_=re.compile(r'tm-votes-meter__value'))
        if score_tag:
            score_text = score_tag.text.strip().replace('+', '')
            try:
                score = int(score_text)
            except ValueError:
                pass
        
        articles_data.append({
            'id': str(article_id),
            'title': title,
            'url': link,
            'date': pub_date,
            'score': score
        })
    return articles_data

def save_articles_to_db(articles_data: List[dict], db: Session):
    for data in articles_data:
        # Check if article exists
        db_article = db.query(models.Article).filter(models.Article.id == data['id']).first()
        if not db_article:
            db_article = models.Article(
                id=data['id'],
                url=data['url'],
                score=data['score']
            )
            db.add(db_article)
            db.flush()
        else:
            db_article.score = data['score']
            db_article.is_active = True # Found in feed, so active
        
        # Sync content and version
        scraper.sync_article(data['id'], db)
    db.commit()

@app.get("/api/top", response_model=List[ArticleSchema])
def get_top_articles(period: Literal["daily", "weekly"] = Query("daily"), db: Session = Depends(get_db)):
    """Returns JSON list of top articles, syncs with DB"""
    url = f"https://habr.com/ru/articles/top/{period}/"
    response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to fetch Habr top articles")
        
    articles_data = extract_articles_from_html(response.text)
    save_articles_to_db(articles_data, db)
    
    # Query back from DB to get joined info
    # For MVP simplicity, we just return the parsed data but it's now in DB
    result = []
    for art in articles_data:
        result.append({
            "id": art['id'],
            "title": art['title'],
            "url": art['url'],
            "date": art['date'].isoformat(),
            "score": art['score'],
            "is_active": True
        })
    return result

@app.get("/api/articles/{article_id}")
def get_article_content(article_id: str, db: Session = Depends(get_db)):
    """Returns the latest HTML content of an article from DB"""
    latest_version = db.query(models.ArticleVersion)\
        .filter(models.ArticleVersion.article_id == article_id)\
        .order_by(models.ArticleVersion.fetched_at.desc())\
        .first()
    
    if not latest_version:
        # Try to fetch on demand
        scraper.sync_article(article_id, db)
        db.commit()
        latest_version = db.query(models.ArticleVersion)\
            .filter(models.ArticleVersion.article_id == article_id)\
            .order_by(models.ArticleVersion.fetched_at.desc())\
            .first()
            
    if not latest_version:
        raise HTTPException(status_code=404, detail="Article content not found")
        
    return {
        "id": article_id,
        "title": latest_version.title,
        "content_html": latest_version.content_html,
        "fetched_at": latest_version.fetched_at.isoformat()
    }

@app.get("/api/custom", response_model=List[ArticleSchema])
def get_custom_articles(
    start: str = Query(..., description="Start date in YYYY-MM-DD format"),
    end: str = Query(..., description="End date in YYYY-MM-DD format"),
    sort: Literal["top", "antitop"] = Query("top", description="Sort by score DESC for top, ASC for antitop"),
    db: Session = Depends(get_db)
):
    # This currently still scrapes on demand but saves to DB
    # Real "Job" logic with percentages is next step
    try:
        start_date = datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end_date = datetime.strptime(end, "%Y-%m-%d").replace(tzinfo=timezone.utc, hour=23, minute=59, second=59)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
        
    articles_results = []
    for page in range(1, 11): # Limit for MVP speed
        url = f'https://habr.com/ru/articles/page{page}/'
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        if response.status_code != 200: break
            
        page_articles = extract_articles_from_html(response.text)
        if not page_articles: break
            
        save_articles_to_db(page_articles, db)
        
        for art in page_articles:
            if start_date <= art['date'] <= end_date:
                articles_results.append(art)
                
        if page_articles[-1]['date'] < start_date: break
            
    reverse_sort = (sort == "top")
    sorted_list = sorted(articles_results, key=lambda x: x['score'], reverse=reverse_sort)
    
    return [{
        "id": a['id'],
        "title": a['title'],
        "url": a['url'],
        "date": a['date'].isoformat(),
        "score": a['score'],
        "is_active": True
    } for a in sorted_list]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
