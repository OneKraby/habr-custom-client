# Habr API Research Report

## 1. Fetching Articles for Custom Date Ranges
Habr does not have an official, documented API that allows fetching articles for arbitrary exact date ranges (e.g., "From 2023-01-01 to 2023-01-03"). 
While there is an unofficial search API (`https://habr.com/kek/v2/articles/?query=...`), testing showed that Elasticsearch date-range operators like `date:[YYYY-MM-DD TO YYYY-MM-DD]` or `time_published:[... TO ...]` do not work as expected and often return 0 results or ignore the range entirely.

**The Solution:**
The most reliable way to fetch articles for a specific period (especially a recent one, like a custom 3-day window) is to iterate through the main chronological feed.
- **Via HTML Parsing:** Scrape `https://habr.com/ru/articles/page{N}/`.
- **Via Unofficial API:** Fetch `https://habr.com/kek/v2/articles/` with a pagination cursor (though HTML scraping is less strictly rate-limited and easier to paginate).

Since Habr restricts chronological pagination to the last 50 pages (approx. 1000 articles, representing roughly 8-10 days of content), this method is perfect for fetching a "recent custom 3-day period". If you need to go further back in time, you would either have to scrape Hub-specific pages, rely on search engine indices, or continuously archive the RSS feed.

## 2. Retrieving the "Anti-Top" (Worst Rated Articles)
Habr does not feature an official "Anti-Top" endpoint or sorting option (e.g., `sort=-rating` does not work in their API).

**The Solution:**
To determine the worst-rated articles for a given period:
1. Fetch all articles within the targeted date range (using the pagination technique described above).
2. Extract the `score` (rating) for each article.
3. Sort the collected articles locally by `score` in **ascending order**.
The items at the top of this sorted list represent the "Anti-Top" for that period.

## 3. Proof of Concept
A Python proof-of-concept script has been created at `scripts/habr_research.py`.
- It uses `requests` and `BeautifulSoup` to scrape the chronological feed up to 50 pages.
- It stops early once it encounters articles older than the requested `start_date`.
- It extracts the `title`, `url`, `date`, and `score`.
- It sorts the dataset to display the **Top 5** and **Anti-Top 5** articles for the specified window.
