# app.py
import streamlit as st
import csv
from datetime import datetime
from pathlib import Path

# ====================== HELPER FUNCTIONS ======================

def parse_date(date_str):
    date_str = str(date_str).strip()
    formats = ['%m/%d/%Y', '%Y%m%d', '%Y-%m-%d', '%d/%m/%Y', '%m-%d-%Y']
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).strftime('%m-%d-%Y')
        except:
            continue
    return date_str

def extract_amount(row, bank_type):
    try:
        if bank_type == 'bmo':
            return -float(str(row[4]).strip().replace('$', '').replace(',', ''))
        else:  # Simplii style
            out = float(str(row[2]).strip().replace('$', '').replace(',', '') or 0)
            inn = float(str(row[3]).strip().replace('$', '').replace(',', '') or 0)
            return inn - out
    except:
        return None

def get_category(desc):
    d = desc.lower()
    if any(k in d for k in ['poke', 'sushi', 'pho', 'pizza', 'mcdonald', 'tim hortons', 'hot pot', 'korean bbq']):
        return 'Dining'
    if any(k in d for k in ['save on foods', 'superstore', 'walmart', 'safeway']):
        return 'Groceries'
    if any(k in d for k in ['hair', 'salon', 'beauty']):
        return 'Personal Care'
    if 'payment thank you' in d or 'paiemen' in d:
        return 'Payment/Bills'
    if any(k in d for k in ['pokemon', 'lounge']):
        return 'Entertainment'
    return 'Other'

def get_source_from_filename(filename):
    name = filename.lower()
    if 'simplii' in name: return 'Simplii'
    elif 'bmo' in name: return 'BMO'
    elif 'cibc' in name: return 'CIBC'
    elif 'rbc' in name: return 'RBC'
    elif 'td' in name: return 'TD'
    else: return Path(filename).stem.upper()

def standardize_file(file_path, source):
    transactions = []
    try:
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            for row in reader:
                if not row or len(row) < 3:
                    continue
                
                text = ' '.join(str(x) for x in row).lower()
                if any(word in text for word in ['funds out', 'transaction details', 'following data', 'item #', 'card #']):
                    continue

                date_str = str(row[0])
                desc = str(row[1])
                bank_type = 'bmo' if (len(row) >= 6 and str(row[2]).strip().isdigit() and len(str(row[2]).strip()) == 8) else 'generic'

                if bank_type == 'bmo':
                    date_str = row[2]
                    desc = row[5] if len(row) > 5 else row[1]

                amount = extract_amount(row, bank_type)
                if amount is not None:
                    date_formatted = parse_date(date_str)
                    category = get_category(desc)
                    transactions.append([date_formatted, str(desc).strip('" '), round(amount, 2), source, category])
    except Exception as e:
        st.error(f"Error processing {file_path.name}: {e}")
    return transactions

# ====================== STREAMLIT APP ======================

st.set_page_config(page_title="Bank CSV Standardizer V2", layout="wide")
st.title("💰 Bank CSV Standardizer V2")
st.markdown("Upload CSVs from any bank • Auto-categorization included")

uploaded_files = st.file_uploader(
    "Upload your bank CSV files (multiple allowed)", 
    type="csv", 
    accept_multiple_files=True
)

if uploaded_files:
    all_transactions = []
    progress_bar = st.progress(0)

    for i, uploaded_file in enumerate(uploaded_files):
        progress_bar.progress((i + 1) / len(uploaded_files))
        
        # Save uploaded file temporarily
        temp_path = Path(f"temp_{uploaded_file.name}")
        temp_path.write_bytes(uploaded_file.getvalue())
        
        source = get_source_from_filename(uploaded_file.name)
        transactions = standardize_file(temp_path, source)
        all_transactions.extend(transactions)
        
        temp_path.unlink(missing_ok=True)

    # Sort by date (newest first)
    all_transactions.sort(key=lambda x: datetime.strptime(x[0], '%m-%d-%Y'), reverse=True)

    st.success(f"✅ Successfully processed **{len(all_transactions)} transactions** from {len(uploaded_files)} files!")

    # Summary Metrics
    col1, col2, col3 = st.columns(3)
    total_amount = sum(row[2] for row in all_transactions)
    col1.metric("Net Amount", f"${total_amount:,.2f}")
    col2.metric("Total Transactions", len(all_transactions))
    col3.metric("Categories", len(set(row[4] for row in all_transactions)))

    # Data Table
    st.subheader("Processed Transactions")
    st.dataframe(
        all_transactions,
        column_config={
            0: "Date",
            1: "Store / Vendor",
            2: "Amount",
            3: "Source",
            4: "Category"
        },
        use_container_width=True,
        hide_index=True
    )

    # Download
    csv_data = "Date (MM-DD-YYYY),Store / Vendor,$ Amount,Source,Category\n"
    csv_data += "\n".join([",".join(map(str, row)) for row in all_transactions])
    
    st.download_button(
        label="📥 Download Standardized CSV",
        data=csv_data,
        file_name="standardized_transactions_v2.csv",
        mime="text/csv"
    )

else:
    st.info("👆 Please upload one or more bank CSV files to begin.")