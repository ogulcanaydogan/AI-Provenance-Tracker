# Firefox Extension (MVP)

Firefox package for analyzing visible text on the current page via the backend API.

## Features

- Extracts readable text from the active tab
- Sends text to `POST /api/v1/detect/text`
- Displays verdict, confidence, model prediction, and explanation
- Persists API base URL in extension storage

## Local Setup (Firefox)

1. Start backend API on `http://localhost:8000` (or your preferred URL).
2. Open Firefox and navigate to `about:debugging#/runtime/this-firefox`.
3. Click **Load Temporary Add-on**.
4. Select `extension-firefox/manifest.json`.
5. Open the extension popup and confirm the API URL.
6. Click **Analyze This Page** on any normal website tab.

## Notes

- This package uses Firefox Manifest V3 with `browser_specific_settings`.
- Internal Firefox pages (`about:*`) cannot be analyzed.
- Text is trimmed to the backend max input size (`50,000` characters).
