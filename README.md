# Habr Custom Client

A custom Habr client for Android featuring custom date ranges for Top and Anti-Top articles.

## Architecture
- **Backend (Middleware)**: Python/FastAPI server to aggregate, cache, and parse Habr.com HTML/API. Resolves custom period requests and anti-top tracking without overloading the mobile client.
- **Android App**: Native Android app written in Kotlin using Jetpack Compose. Fetches structured JSON data from the Middleware.

## Roadmap
1. [ ] MVP Backend & API Research (Top/Anti-Top, custom dates)
2. [ ] MVP Android App (Top of the day feed)
3. [ ] Hubs & Comments parsing
4. [ ] Custom Date & Anti-top interface on Android
5. [ ] Polishing (Auth, offline cache, Dark theme)
