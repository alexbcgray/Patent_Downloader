import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import zipfile
import io

# --- App UI Configuration ---
st.set_page_config(page_title="Patent Downloader", page_icon="📄")
st.title("Automated Patent Downloader 📄")
st.write("Drag and drop your Excel file containing a 'Publication number' column. The app will fetch the PDFs and package them into a single Zip file for you.")

# --- Browser Spoofing ---
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# --- File Uploader ---
uploaded_file = st.file_uploader("Upload your Excel File (.xlsx)", type=["xlsx"])

if uploaded_file is not None:
    # Read the excel file
    try:
        df = pd.read_excel(uploaded_file)
        if 'Publication number' not in df.columns:
            st.error("Error: The Excel file must contain a column named 'Publication number'.")
            st.stop()
            
        patents_to_fetch = df['Publication number'].dropna().astype(str).tolist()
        st.success(f"Found {len(patents_to_fetch)} patents to process.")
        
    except Exception as e:
        st.error(f"Could not read the Excel file: {e}")
        st.stop()

    # --- Process Button ---
    if st.button("Fetch Patents"):
        # UI Elements for progress
        progress_bar = st.progress(0)
        status_text = st.empty()
        log_window = st.empty()
        
        # Create an in-memory bytes buffer for our zip file
        zip_buffer = io.BytesIO()
        
        # Open the zip buffer for writing
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            
            logs = []
            successful_downloads = 0
            
            for i, pub_number in enumerate(patents_to_fetch):
                pub_number = pub_number.strip()
                status_text.markdown(f"**Currently processing:** `{pub_number}` ({i+1}/{len(patents_to_fetch)})")
                
                patent_page_url = f"https://patents.google.com/patent/{pub_number}/en"
                
                try:
                    # 1. Load Google Patents Page
                    page_response = requests.get(patent_page_url, headers=HEADERS)
                    
                    if page_response.status_code == 200:
                        soup = BeautifulSoup(page_response.text, 'html.parser')
                        meta_tag = soup.find('meta', attrs={'name': 'citation_pdf_url'})
                        
                        if meta_tag and meta_tag.get('content'):
                            real_pdf_url = meta_tag['content']
                            
                            # 2. Download the actual PDF
                            pdf_response = requests.get(real_pdf_url, headers=HEADERS)
                            
                            if pdf_response.status_code == 200:
                                # Write the PDF bytes directly into the Zip file
                                zip_file.writestr(f"{pub_number}.pdf", pdf_response.content)
                                logs.append(f"✅ Success: {pub_number}")
                                successful_downloads += 1
                            else:
                                logs.append(f"❌ Failed to download PDF data: {pub_number}")
                        else:
                            logs.append(f"⚠️ No PDF link found on page: {pub_number}")
                    else:
                        logs.append(f"❌ Could not load page: {pub_number}")
                        
                except Exception as e:
                    logs.append(f"⚠️ Error on {pub_number}: {e}")
                
                # Update progress bar and logs
                progress_bar.progress((i + 1) / len(patents_to_fetch))
                # Keep only the last 5 logs so the UI doesn't get massive
                log_window.text("\n".join(logs[-5:]))
                
                time.sleep(1.5) # Be polite to Google

        # --- Finished Processing ---
        progress_bar.empty()
        status_text.success(f"🎉 Complete! Successfully bundled {successful_downloads} out of {len(patents_to_fetch)} patents.")
        
        # Provide the download button for the Zip file
        st.download_button(
            label="⬇️ Download All Patents (ZIP)",
            data=zip_buffer.getvalue(),
            file_name="Downloaded_Patents.zip",
            mime="application/zip"
        )
