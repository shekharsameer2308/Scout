# Project Rules and Styling Constraints

This project enforces strict coding, styling, and architectural rules to ensure consistency and reliability. All agents working on this workspace must comply with these guidelines.

## 🎨 Design System & Aesthetics
- **No Colorful Gradients or Neon Headers**: Keep headers, subheaders, and dashboards minimalist and neutral.
- **No Emojis in Text/Headers**: Remove decorative emojis from headings, section subheaders, and alerts (unless specifically requested by the user).
- **Muted Color Scheme**: Use the colors defined in [styles.py](file:///Users/sameershekhar/Documents/GitHub/LLM-/frontend/styles.py) (Slate `#475569`, Emerald `#10b981`, Red `#ef4444`, and Gray `#6b7280`).
- **Standardized Elements**: Wrap list items in `<div class="content-card">` and tags/labels in `<span class="neutral-badge">`.

## 🔄 Streamlit Button Synchronization
- Suggestion/Quick action buttons must modify their backing session state keys directly and instantly execute logic. Do not write logic that relies on `st.rerun()` or double-clicks.
- Always use:
  ```python
  product_query = button_query or sidebar_query
  ```
  to resolve queries on the same frame.

## 🚀 Database Connections (psycopg2 & Render compatibility)
- Remove `?pgbouncer=true` or other custom query params from PostgreSQL strings before passing to SQLAlchemy.
- Use `clean_database_url` from `database.connection` to wrap connection parameters in `connection.py` and Alembic `env.py` scripts.
