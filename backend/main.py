import re
from datetime import datetime, timezone
from typing import List, Literal, Optional

import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

app = FastAPI(title="Habr Custom API")

class Article(BaseModel):
    title: str
    url: str
    date: str
    score: int

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
            'title': title,
            'url': link,
            'date': pub_date,
            'score': score
        })
    return articles_data

@app.get("/api/top", response_model=List[Article])
def get_top_articles(period: Literal["daily", "weekly"] = Query("daily")):
    """Returns JSON list of top articles"""
    url = f"https://habr.com/ru/articles/top/{period}/"
    response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to fetch Habr top articles")
        
    articles_data = extract_articles_from_html(response.text)
    
    # Format dates as strings
    result = []
    for art in articles_data:
        art['date'] = art['date'].isoformat()
        result.append(Article(**art))
        
    return result

@app.get("/api/custom", response_model=List[Article])
def get_custom_articles(
    start: str = Query(..., description="Start date in YYYY-MM-DD format"),
    end: str = Query(..., description="End date in YYYY-MM-DD format"),
    sort: Literal["top", "antitop"] = Query("top", description="Sort by score DESC for top, ASC for antitop")
):
    """Parses articles within that range, sorts by score ASC for antitop, DESC for top."""
    try:
        start_date = datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end_date = datetime.strptime(end, "%Y-%m-%d").replace(tzinfo=timezone.utc, hour=23, minute=59, second=59)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
        
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="Start date must be before or equal to end date.")
        
    articles_data = []
    # Fetch chronological pages
    for page in range(1, 51):
        url = f'https://habr.com/ru/articles/page{page}/'
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        
        if response.status_code != 200:
            break
            
        page_articles = extract_articles_from_html(response.text)
        if not page_articles:
            break
            
        oldest_date_on_page = page_articles[-1]['date']
        
        for art in page_articles:
            if start_date <= art['date'] <= end_date:
                articles_data.append(art)
                
        if oldest_date_on_page and oldest_date_on_page < start_date:
            break
            
    # Sort articles
    reverse_sort = True if sort == "top" else False
    sorted_articles = sorted(articles_data, key=lambda x: x['score'], reverse=reverse_sort)
    
    result = []
    for art in sorted_articles:
        art['date'] = art['date'].isoformat()
        result.append(Article(**art))
        
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
