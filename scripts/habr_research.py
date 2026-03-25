#!/usr/bin/env python3
"""
habr_research.py
Proof-of-Concept: Fetch Habr articles for a custom 3-day period,
extract their title, URL, date, and score, and display the TOP and ANTI-TOP.
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
import re

# Configuration: Target a recent 3-day window
# Habr restricts chronological pagination to the last 50 pages (approx. 8-10 days).
NOW = datetime.now(timezone.utc)
END_DATE = NOW - timedelta(days=1)
START_DATE = END_DATE - timedelta(days=3)

def parse_habr_date(datetime_str):
    """Parse Habr's ISO 8601 datetime format."""
    # e.g., "2026-03-25T16:15:57.000Z"
    if datetime_str.endswith('Z'):
        datetime_str = datetime_str[:-1] + '+00:00'
    try:
        return datetime.fromisoformat(datetime_str)
    except ValueError:
        return None

def fetch_articles_in_range(start_date, end_date):
    """Fetch articles from Habr chronologically until we pass the start_date."""
    print(f"[*] Fetching articles from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}...")
    articles_data = []
    
    # Iterate through Habr pages. Max is 50.
    for page in range(1, 51):
        url = f'https://habr.com/ru/articles/page{page}/'
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        
        if response.status_code != 200:
            print(f"[*] Stopped at page {page} (Status: {response.status_code})")
            break
            
        soup = BeautifulSoup(response.text, 'html.parser')
        articles = soup.find_all('article')
        
        if not articles:
            break
            
        oldest_date_on_page = None
        for art in articles:
            time_tag = art.find('time')
            if not time_tag or not time_tag.has_attr('datetime'):
                continue
                
            pub_date = parse_habr_date(time_tag['datetime'])
            if not pub_date:
                continue
                
            oldest_date_on_page = pub_date
            
            # Filter by date range
            if start_date <= pub_date <= end_date:
                # Extract title
                title_tag = art.find('h2')
                title = title_tag.text.strip() if title_tag else "No Title"
                
                # Extract URL
                link_tag = art.find('a', class_='tm-title__link')
                link = f"https://habr.com{link_tag['href']}" if link_tag and link_tag.has_attr('href') else ""
                
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
        
        # Stop fetching if the oldest article on this page is older than our start_date
        if oldest_date_on_page and oldest_date_on_page < start_date:
            print(f"[*] Reached articles older than {start_date.strftime('%Y-%m-%d')} at page {page}.")
            break

    return articles_data

def main():
    articles = fetch_articles_in_range(START_DATE, END_DATE)
    print(f"[*] Found {len(articles)} articles in the specified 3-day window.\n")
    
    if not articles:
        return

    # Sort articles by score (ASC for anti-top, DESC for top)
    sorted_articles = sorted(articles, key=lambda x: x['score'])
    
    print("="*60)
    print("📉 ANTI-TOP (Worst Rated Articles):")
    print("="*60)
    for idx, art in enumerate(sorted_articles[:5], 1):
        print(f"{idx}. [Score: {art['score']:>3}] {art['title']}")
        print(f"   Date: {art['date'].strftime('%Y-%m-%d %H:%M:%S')} | {art['url']}")
        
    print("\n" + "="*60)
    print("🏆 TOP (Best Rated Articles):")
    print("="*60)
    for idx, art in enumerate(reversed(sorted_articles[-5:]), 1):
        print(f"{idx}. [Score: {art['score']:>3}] {art['title']}")
        print(f"   Date: {art['date'].strftime('%Y-%m-%d %H:%M:%S')} | {art['url']}")

if __name__ == "__main__":
    main()
