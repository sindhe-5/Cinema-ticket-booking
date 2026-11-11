# Cinema Group Ticket Booking System — Streamlit

A Python Streamlit version of the Cinema Group Ticket Booking and Mutex Dashboard.

## Run locally

```bash
python -m pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Deploy on Streamlit Community Cloud

1. Create a GitHub repository and upload `streamlit_app.py`, `requirements.txt`, and `README.md`.
2. Visit https://share.streamlit.io and sign in with GitHub.
3. Click **Create app**.
4. Select your repository, branch (`main`), and main file path (`streamlit_app.py`).
5. Click **Deploy**.

## Project note

The Streamlit interface and booking logic are written in Python. The mutex-on simulation processes requests one at a time. The mutex-off simulation deliberately separates availability checks from updates so overlapping requests can demonstrate a race condition and double booking. This is an educational simulation rather than a production ticketing system.

Booking data is held in Streamlit session state and is not a permanent database. It may reset when the app session or server restarts.
