import requests
from bs4 import BeautifulSoup, Tag
from sqlalchemy.orm import Session
from datetime import datetime
from .models import Article, ArticleVersion

def fetch_article_content(article_id: str):
    url = f"https://habr.com/ru/articles/{article_id}/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Habr article structure: title is usually in an h1 with class 'tm-title'
    # Content is usually in a div with class 'tm-article-presenter__content' or 'article-formatted-body'
    title_tag = soup.find('h1', class_='tm-title')
    title = title_tag.get_text(strip=True) if title_tag else "No Title"

    content_div = soup.find('div', class_='tm-article-presenter__content')
    if not content_div:
        content_div = soup.find('div', class_='article-formatted-body')
    
    if not content_div:
        return {"title": title, "content_html": ""}

    # Clean the HTML
    allowed_tags = ['p', 'b', 'i', 'img', 'pre', 'code', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'a', 'blockquote']
    
    for tag in content_div.find_all(True):
        if tag.name not in allowed_tags:
            tag.unwrap()
        else:
            # Remove all attributes except 'src' for img and 'href' for a
            attrs = dict(tag.attrs)
            for attr in attrs:
                if tag.name == 'img' and attr == 'src':
                    continue
                if tag.name == 'a' and attr == 'href':
                    continue
                del tag[attr]

    # Remove script tags and comments (though unwrap might have handled some)
    for script in content_div(["script", "style"]):
        script.decompose()

    content_html = str(content_div.decode_contents()).strip()
    
    return {
        "title": title,
        "content_html": content_html
    }

def sync_article(article_id: str, db: Session):
    # Check if article exists
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        # If not exists, create it
        article = Article(id=article_id, url=f"https://habr.com/ru/articles/{article_id}/")
        db.add(article)
        db.commit()
        db.refresh(article)

    # Fetch latest content
    data = fetch_article_content(article_id)
    
    # Get latest version
    latest_version = db.query(ArticleVersion)\
        .filter(ArticleVersion.article_id == article_id)\
        .order_by(ArticleVersion.fetched_at.desc())\
        .first()

    # Create new version if content changed or no version exists
    if not latest_version or latest_version.content_html != data['content_html'] or latest_version.title != data['title']:
        new_version = ArticleVersion(
            article_id=article_id,
            title=data['title'],
            content_html=data['content_html'],
            fetched_at=datetime.utcnow()
        )
        db.add(new_version)
        
        # Update Article updated_at (handled by onupdate in model, but setting it explicitly ensures it changes)
        article.updated_at = datetime.utcnow()
        db.commit()
        return True
    
    return False
