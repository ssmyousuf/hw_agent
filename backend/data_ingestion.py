import pandas as pd
import dateutil.parser
import pypdf
import re

def categorize_merchant(description: str) -> str:
    """
    Simple keyword-based categorization.
    """
    desc = description.upper()
    
    # Common categories for Indian bank statements
    categories = {
        "Food & Dining": ["SWIGGY", "ZOMATO", "RESTAURANT", "FOOD", "CAFE", "BAKERY", "PAYTM*SWIGGY", "PAPA JOHNS", "DOMINOS", "BUNDL", "GEETHAM", "AMBUR"],
        "Shopping": ["AMAZON", "FLIPKART", "MYNTR", "ZUDIO", "RETAIL", "SHOPPING", "TRENT", "AJIO", "TATA", "NYKAA", "GRACE MART", "ASSPL"],
        "Travel": ["REDBUS", "IRCTC", "UBER", "OLA", "AIRASIA", "INDIGO", "MAKEMYTRIP"],
        "Education": ["AAKASH", "SCHOOL", "UNI", "COLLEGE", "EDUCATION", "VE SCHOOL"],
        "Entertainment": ["NETFLIX", "PRIME VIDEO", "BOOKMYSHOW", "HOTSTAR", "DISNEY", "PLAYSTATION", "MIRAJ", "ZEE"],
        "Fuel": ["PETRO", "BPCL", "HPCL", "IOCL", "SHELL", "SURCHARGE"],
        "Bills & Services": ["AIRTEL", "ACT", "JIO", "RECHARGE", "BBPS", "BILL", "INSURANCE", "LIC", "ELECTRICITY"],
        "Financial": ["AUTOPAY", "EMI", "INTEREST", "CHARGES", "CASHBACK", "REWARD", "BANK", "ST260", "ST253"]
    }
    
    for category, keywords in categories.items():
        if any(kw in desc for kw in keywords):
            return category
            
    return "Uncategorized"

def parse_pdf(filepath: str, password: str = None) -> pd.DataFrame:
    """
    Parses a PDF file attempting to extract transactions.
    Strategy: pattern match lines that start with a date.
    """
    transactions = []
    
    # Relaxed Regex Patterns
    # Date detection: Look for standard date formats at the start of the string (allowing for leading spaces)
    date_pattern = re.compile(r'^\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\w{3}\s+\d{1,2})', re.IGNORECASE)
    
    # Amount detection: Look for a number with an optional decimal part at the end of the line
    # Allows for 'Cr', 'Dr', and trailing spaces
    amount_pattern = re.compile(r'(-?\$?[\d,]+(\.\d{1,2})?)\s*(CR|DR)?\s*$', re.IGNORECASE)

    try:
        reader = pypdf.PdfReader(filepath)
        
        if reader.is_encrypted:
            if password:
                reader.decrypt(password)
            else:
                print("PDF is encrypted but no password provided.")
                return pd.DataFrame() 

        debug_log = []
        
        for page_num, page in enumerate(reader.pages):
            try:
                text = page.extract_text()
            except Exception:
                continue 
                
            if not text: continue
            
            lines = text.split('\n')
            debug_log.append(f"--- Page {page_num} ---")
            
            for line in lines:
                # Pre-clean: Replace '|' with space and remove noise from ends
                line_clean = line.replace('|', ' ').strip()
                # Remove common stray trailing characters like 'l' or 'i' or '|'
                line_clean = re.sub(r'[\s|liI\+]*$', '', line_clean)
                
                # HDFC Specfic: Remove reward points metadata like "+ 30" or "C 30" appearing before the amount
                # These are usually separated by spaces
                line_clean = re.sub(r'\s+[\+\s]*\d+\s+(?=C)', ' ', line_clean)
                line_clean = re.sub(r'\s+', ' ', line_clean).strip()
                    
                debug_log.append(f"Cleaned Line: {line_clean}")

                date_match = date_pattern.search(line_clean)
                amount_match = amount_pattern.search(line_clean)
                
                if date_match and amount_match:
                    date_str = date_match.group(1)
                    amount_str = amount_match.group(1)
                    debug_log.append(f"  -> MATCH: Date={date_str}, Amount={amount_str}")
                    
                    # Normalize date to YYYY-MM-DD for consistent filtering
                    try:
                        # Try parsing with dateutil (handles many formats)
                        parsed_date = dateutil.parser.parse(date_str, dayfirst=True)
                        iso_date = parsed_date.strftime('%Y-%m-%d')
                    except Exception:
                        iso_date = date_str  # Fallback
                        
                    # Description is everything in between
                    date_end_idx = date_match.end()
                    amount_start_idx = amount_match.start()
                    
                    if amount_start_idx > date_end_idx:
                        description = line_clean[date_end_idx:amount_start_idx].strip()
                        
                        # Clean amount
                        try:
                            amount_val_str = amount_str.replace('$', '').replace(',', '')
                            amount_val = float(amount_val_str)
                            
                            # Check for 'C' or 'CR' in the line AFTER the description but BEFORE/NEAR amount
                            # HDFC often uses " C " to denote a Credit (payment).
                            if re.search(r'\sC(R)?\s', line_clean, re.IGNORECASE):
                                amount_val = -amount_val
                            
                            transactions.append({
                                "date": iso_date,
                                "description": description,
                                "amount": amount_val,
                                "category": categorize_merchant(description)
                            })
                        except Exception:
                            pass
        
        # Write debug log
        with open("debug_pdf_log.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(debug_log))
            
        return pd.DataFrame(transactions)
    except Exception as e:
        print(f"Error parsing PDF: {e}")
        return pd.DataFrame()

def load_statement(filepath: str, password: str = None) -> pd.DataFrame:
    """
    Loads a credit card statement from a CSV or PDF file.
    """
    if filepath.endswith('.pdf'):
        return parse_pdf(filepath, password)
    else:
        try:
            df = pd.read_csv(filepath)
            
            # Normalize headers
            df.columns = [c.strip().lower() for c in df.columns]
            
            # basic mapping if columns are slightly different
            column_map = {
                'date': 'date',
                'transaction date': 'date',
                'description': 'description',
                'merchant': 'description',
                'amount': 'amount',
                'debit': 'amount',
                'category': 'category'
            }
            
            df = df.rename(columns=column_map)
            
            # Ensure required columns
            required = ['date', 'description', 'amount']
            missing = [c for c in required if c not in df.columns]
            if missing:
                raise ValueError(f"Missing columns: {missing}")
                
            # Parse Dates
            df['date'] = df['date'].apply(lambda x: dateutil.parser.parse(str(x)).strftime('%Y-%m-%d'))
            
            # Ensure Amount is numeric
            # Handle cases where amount might be "$1,200.00"
            if df['amount'].dtype == 'O':
                # Use raw string for regex to avoid syntax warning
                df['amount'] = df['amount'].replace(r'[\$,]', '', regex=True).astype(float)
                
            return df
        except Exception as e:
            print(f"Error loading statement: {e}")
            return pd.DataFrame()

def query_transactions(df: pd.DataFrame, start_date: str = None, end_date: str = None, category: str = None, min_amount: float = None):
    """
    Filters transactions based on criteria.
    """
    if df.empty:
        return []
        
    mask = pd.Series([True] * len(df))
    
    if start_date:
        mask &= (df['date'] >= start_date)
    if end_date:
        mask &= (df['date'] <= end_date)
        
    if category:
        # Search in BOTH 'category' and 'description' columns
        cat_mask = pd.Series([False] * len(df))
        
        if 'category' in df.columns:
            cat_mask |= (df['category'].str.contains(category, case=False, na=False))
            
        if 'description' in df.columns:
            cat_mask |= (df['description'].str.contains(category, case=False, na=False))
            
        mask &= cat_mask

    if min_amount:
        mask &= (df['amount'].abs() >= min_amount)
        
    return df[mask].to_dict('records')

def get_spending_summary(df: pd.DataFrame, group_by: str = 'category'):
    """
    Summarizes spending by category or month.
    """
    if df.empty:
        return {}
        
    if group_by == 'category' and 'category' in df.columns:
        return df.groupby('category')['amount'].sum().to_dict()
    elif group_by == 'month':
        df['month'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m')
        return df.groupby('month')['amount'].sum().to_dict()
    
    return {"total": df['amount'].sum()}
