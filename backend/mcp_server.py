from mcp.server.fastmcp import FastMCP
from backend.data_ingestion import load_statement, query_transactions, get_spending_summary
import pandas as pd
import os

# Initialize FastMCP Server
mcp = FastMCP("CreditCardAgent")

# Global state to hold the current dataframe
# In a real app, this might be session-scoped or in a DB
current_df = pd.DataFrame()

def set_dataframe(df: pd.DataFrame):
    global current_df
    current_df = df

@mcp.tool()
def read_transactions(start_date: str = None, end_date: str = None, category: str = None, min_amount: float = None) -> str:
    """
    Search for transactions in the credit card statement based on filters.
    
    Args:
        start_date (str): format YYYY-MM-DD
        end_date (str): format YYYY-MM-DD
        category (str): Filter by category or merchant name (partial match)
        min_amount (float): Minimum transaction amount
    """
    global current_df
    if current_df.empty:
        return "No statement loaded. Please upload a statement first."
        
    # Cast min_amount to float to avoid pandas errors if the LLM sent a string
    if min_amount is not None:
        try:
            min_amount = float(min_amount)
        except:
            min_amount = None
            
    results = query_transactions(current_df, start_date, end_date, category, min_amount)
    return str(results)

@mcp.tool()
def summarize_spending(group_by: str = "category") -> str:
    """
    Get a summary of spending grouped by 'category' or 'month'.
    
    Args:
        group_by (str): 'category' or 'month'
    """
    global current_df
    if current_df.empty:
        return "No statement loaded."
        
    summary = get_spending_summary(current_df, group_by)
    return str(summary)

@mcp.tool()
def generate_spending_chart(group_by: str = "category", chart_type: str = "bar") -> str:
    """
    Generate a chart of spending and return the image URL.
    
    Args:
        group_by (str): 'category' or 'month'
        chart_type (str): 'bar' or 'pie'
    """
    global current_df
    import matplotlib
    matplotlib.use('Agg') # Non-interactive backend
    import matplotlib.pyplot as plt
    import uuid
    
    if current_df.empty:
        return "No statement loaded."

    try:
        data = get_spending_summary(current_df, group_by)
        if not data:
            return "No data to chart."
            
        # Filter out positive values (income) and take absolute of expenses for cleaner charts?
        # Or just chart what we get. The summary typically returns raw sums. 
        # Expenses are typically negative. Let's make them positive for the chart.
        chart_data = {k: abs(v) for k, v in data.items() if v < 0} # Only expenses
        
        if not chart_data:
            # If no expenses (only income?), fallback to all
             chart_data = {k: abs(v) for k, v in data.items()}
             
        labels = list(chart_data.keys())
        values = list(chart_data.values())
        
        plt.figure(figsize=(10, 6))
        
        if chart_type == "pie":
            plt.pie(values, labels=labels, autopct='%1.1f%%', startangle=140)
            plt.title(f"Spending by {group_by.capitalize()}")
        else:
            plt.bar(labels, values, color='skyblue')
            plt.xlabel(group_by.capitalize())
            plt.ylabel("Amount (₹)")
            plt.title(f"Spending by {group_by.capitalize()}")
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            
        # Save to frontend/charts
        filename = f"chart_{uuid.uuid4().hex[:8]}.png"
        charts_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "charts")
        os.makedirs(charts_dir, exist_ok=True)
        filepath = os.path.join(charts_dir, filename)
        
        plt.savefig(filepath)
        plt.close()
        
        return f"![Spending Chart](/charts/{filename})"
    except Exception as e:
        return f"Error generating chart: {str(e)}"

@mcp.resource("statement://current")
def get_current_statement() -> str:
    """
    Get the full current statement as CSV text.
    """
    global current_df
    if current_df.empty:
        return "Empty"
    return current_df.to_csv(index=False)
