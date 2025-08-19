# enrichment.py
# Module 2: Gathers deterministic OSINT data for a given lead.
# v2_2025-08-18: Replaced placeholders with live web search functions.

import os
import json
import pandas as pd
from time import sleep

# --- Dependencies ---
# This module requires the following packages:
# pip install duckduckgo-search googlesearch-python
from duckduckgo_search import DDGS
from googlesearch import search as google_search

# --- Core Web Search Function ---

def perform_web_searches(company_name: str, prospect_name: str, num_results: int = 5):
    """
    Performs a series of targeted web searches on Google and DuckDuckGo
    to gather intelligence about a company and a prospect.

    Args:
        company_name (str): The name of the target company.
        prospect_name (str): The name of the target prospect.
        num_results (int): The number of results to fetch per query.

    Returns:
        dict: A dictionary containing lists of search results for each query.
    """
    print(f"  [ENRICH] Starting web searches for '{prospect_name} at {company_name}'...")
    
    # Define intelligent search queries to find specific information
    search_queries = {
        "recent_news": f'"{company_name}" news funding OR expansion OR "press release" OR acquisition',
        "prospect_role": f'"{prospect_name}" "{company_name}" title OR role site:linkedin.com',
        "company_profile": f'"{company_name}" company profile overview OR "about us"',
    }
    
    all_results = {}
    
    for key, query in search_queries.items():
        print(f"    -> Running query for: {key}")
        query_results = []
        
        # 1. Search with DuckDuckGo (API-based, more reliable)
        try:
            with DDGS() as ddgs:
                ddgs_results = list(ddgs.text(query, max_results=num_results))
                for result in ddgs_results:
                    query_results.append({
                        "source": "DuckDuckGo",
                        "title": result.get('title'),
                        "link": result.get('href'),
                        "snippet": result.get('body')
                    })
        except Exception as e:
            print(f"      [WARN] DuckDuckGo search failed for query '{query}': {e}")

        # 2. Search with Google (Scraping-based, use with caution)
        # NOTE: This can be unreliable and may lead to temporary IP blocks from Google.
        # For production, a paid API like SerpApi is strongly recommended.
        try:
            # The sleep() is crucial to avoid being blocked.
            sleep(2) 
            google_results_gen = google_search(query, num_results=num_results, sleep_interval=1)
            for url in google_results_gen:
                 query_results.append({
                    "source": "Google",
                    "title": "N/A (googlesearch library does not provide title/snippet)",
                    "link": url,
                    "snippet": "N/A"
                })
        except Exception as e:
            print(f"      [WARN] Google search failed for query '{query}': {e}")
            
        all_results[key] = query_results
        
    return all_results

# --- Orchestrator Function ---

def enrich_lead(lead_series: pd.Series):
    """
    Orchestrates the enrichment process for a single lead using live web searches.

    Args:
        lead_series (pd.Series): A single row from the leads DataFrame.

    Returns:
        dict: A dictionary containing all the raw intelligence gathered.
    """
    prospect_name = lead_series.get('Prospect_Name', 'N/A')
    company_name = lead_series.get('Company_Name', 'N/A')
    
    print(f"\n--- Enriching Lead: {prospect_name} at {company_name} ---")
    
    if prospect_name == 'N/A' or company_name == 'N/A':
        print("  [ERROR] Lead is missing Prospect_Name or Company_Name. Skipping enrichment.")
        return {"error": "Missing critical lead information."}

    try:
        # The single point of entry for all our research
        intelligence_report = perform_web_searches(company_name, prospect_name)
        
        print("--- Enrichment Complete ---")
        return intelligence_report

    except Exception as e:
        print(f"  [ERROR] An unexpected error occurred during enrichment: {e}")
        return {"error": str(e)}


if __name__ == '__main__':
    # This block allows you to test this module independently.
    # To run this test, you need to install the dependencies:
    # pip install pandas duckduckgo-search googlesearch-python
    
    print("--- Running Enrichment Module Standalone Test ---")

    sample_lead_data = {
        'Prospect_Name': 'Elon Musk',
        'Company_Name': 'SpaceX',
    }
    sample_lead_series = pd.Series(sample_lead_data)

    # Run the enrichment process
    final_report = enrich_lead(sample_lead_series)

    # Print the structured output
    print("\n--- Final Intelligence Report (JSON) ---")
    print(json.dumps(final_report, indent=2))

