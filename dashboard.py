import streamlit as st
import os
import requests
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# Google Sheets
creds = Credentials.from_service_account_info(eval(os.getenv('CREDENTIALS_JSON')))
sheets_service = build('sheets', 'v4', credentials=creds)
sheet_id = os.getenv('SHEET_ID')

st.title("OmniPredatorV4 Dashboard © 2025 Slickofficials HQ by Amson Multi Global LTD")
st.write("Resale rights included. Contact: slickofficials@amsonmultiglobal.com")

# Fetch data from Sheets
sheet = sheets_service.spreadsheets().values().get(spreadsheetId=sheet_id, range="A:A").execute()
data = sheet.get('values', [])

if data:
    st.write("### Recent Logs")
    for row in data[-10:]:  # Last 10 entries
        st.write(row[0])
else:
    st.write("No data yet.")

if st.button("Refresh"):
    st.experimental_rerun()
