# Browser Extension (MVP)

Chrome extension for analyzing visible text on the current page via the backend API.

## Features

- Extracts readable text from the active tab
- Sends text to `POST /api/v1/detect/text`
- Displays verdict, confidence, model prediction, and explanation
- Persists API base URL in extension storage

## Local Setup

1. Start backend API on `http://localhost:8000` (or your preferred URL).
2. Open Chrome and go to `chrome://extensions`.
3. Enable `Developer mode`.
4. Click `Load unpacked`.
5. Select the `extension/` folder in this repository.
6. Open the extension popup and confirm the API URL.
7. Click `Analyze This Page` on any regular website tab.

## Notes

- This MVP targets Chrome Manifest V3.
- Chrome internal pages (for example `chrome://...`) cannot be analyzed.
- Text is trimmed to the backend max input size (`50,000` characters).
