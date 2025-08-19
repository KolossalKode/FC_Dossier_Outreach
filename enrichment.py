# enrichment.py
# Module 2: Gathers deterministic OSINT data for a given lead.
# v4_2025-08-18: Enhanced with Gemini AI industry detection and comprehensive search strategies

import os
import json
import pandas as pd
from time import sleep
import random
import google.generativeai as genai

# --- Dependencies ---
# This module requires the following packages:
# pip install duckduckgo-search googlesearch-python google-generativeai
from duckduckgo_search import DDGS
from googlesearch import search as google_search

# --- Gemini AI Configuration ---
try:
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY environment variable not found.")
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel('gemini-2.5-pro')
    print("Gemini API configured successfully with 'gemini-2.5-pro' for industry detection.")
except Exception as e:
    print(f"Error configuring Gemini API: {e}")
    gemini_model = None

# --- Enhanced Search Queries ---

def generate_search_queries(company_name: str, prospect_name: str, industry: str = None):
    """
    Generates comprehensive search queries for different types of intelligence.
    
    Args:
        company_name: The target company name
        prospect_name: The target prospect name
        industry: The industry the company operates in
    
    Returns:
        dict: Organized search queries by category
    """
    
    # Basic company information
    company_queries = {
        "company_overview": [
            f'"{company_name}" company profile',
            f'"{company_name}" about us',
            f'"{company_name}" company overview',
            f'"{company_name}" business description'
        ],
        "company_news": [
            f'"{company_name}" news',
            f'"{company_name}" press release',
            f'"{company_name}" announcement',
            f'"{company_name}" funding round',
            f'"{company_name}" expansion',
            f'"{company_name}" acquisition',
            f'"{company_name}" partnership'
        ],
        "company_financials": [
            f'"{company_name}" revenue',
            f'"{company_name}" funding',
            f'"{company_name}" investment',
            f'"{company_name}" financial results',
            f'"{company_name}" annual report'
        ]
    }
    
    # Industry-specific research
    industry_queries = {}
    if industry:
        industry_queries = {
            "industry_trends": [
                f'"{industry}" industry trends 2025',
                f'"{industry}" market analysis',
                f'"{industry}" growth opportunities',
                f'"{industry}" challenges'
            ],
            "industry_funding": [
                f'"{industry}" funding trends',
                f'"{industry}" investment opportunities',
                f'"{industry}" capital needs'
            ]
        }
    
    # Prospect-specific research
    prospect_queries = {
        "prospect_role": [
            f'"{prospect_name}" "{company_name}" title role',
            f'"{prospect_name}" "{company_name}" linkedin',
            f'"{prospect_name}" "{company_name}" position',
            f'"{prospect_name}" "{company_name}" executive'
        ],
        "prospect_background": [
            f'"{prospect_name}" professional background',
            f'"{prospect_name}" career history',
            f'"{prospect_name}" business experience'
        ]
    }
    
    # Competitive intelligence
    competitive_queries = {
        "competitors": [
            f'"{company_name}" competitors',
            f'"{company_name}" vs competitors',
            f'"{company_name}" market position'
        ],
        "market_opportunity": [
            f'"{company_name}" growth opportunities',
            f'"{company_name}" market expansion',
            f'"{company_name}" new markets'
        ]
    }
    
    return {
        "company": company_queries,
        "industry": industry_queries,
        "prospect": prospect_queries,
        "competitive": competitive_queries
    }

# --- Industry Detection with Gemini AI ---

def detect_industry_with_gemini(company_name: str, search_results: list):
    """
    Uses Gemini AI to analyze search results and determine the company's industry.
    
    Args:
        company_name: The company name to analyze
        search_results: List of search results to analyze
    
    Returns:
        str: Detected industry or "Unknown"
    """
    if not gemini_model:
        return "Unknown (Gemini not configured)"
    
    try:
        # Prepare search results for analysis
        results_text = ""
        for i, result in enumerate(search_results[:30], 1):  # Analyze first 30 results
            title = result.get('title', 'N/A')
            snippet = result.get('snippet', 'N/A')
            link = result.get('link', 'N/A')
            results_text += f"Result {i}:\nTitle: {title}\nSnippet: {snippet}\nLink: {link}\n\n"
        
        # Create prompt for Gemini
        prompt = f"""
        Analyze the following search results for the company "{company_name}" and determine their primary industry.

        Search Results:
        {results_text}

        Instructions:
        1. Review all the search results carefully
        2. Look for industry indicators in company descriptions, news articles, and business information
        3. Identify the primary industry this company operates in
        4. Return ONLY the industry name (e.g., "Technology", "Healthcare", "Manufacturing", "Retail", "Financial Services")
        5. If you cannot determine the industry from the results, return "Unknown"
        6. Be specific but concise (e.g., "Software Development" not just "Technology")

        Industry:"""

        # Get Gemini's analysis
        response = gemini_model.generate_content(prompt)
        detected_industry = response.text.strip()
        
        print(f"    -> Gemini AI detected industry: {detected_industry}")
        return detected_industry
        
    except Exception as e:
        print(f"    -> [WARN] Gemini industry detection failed: {e}")
        return "Unknown (Analysis failed)"

def perform_industry_detection_search(company_name: str, prospect_phone: str = None, prospect_email: str = None):
    """
    Performs targeted searches to gather information for industry detection.
    
    Args:
        company_name: The company name
        prospect_phone: Phone number (optional)
        prospect_email: Email domain (optional)
    
    Returns:
        list: Search results for industry analysis
    """
    print(f"    -> Performing industry detection search for: {company_name}")
    
    # Generate industry detection queries
    industry_queries = [
        f'"{company_name}" company profile',
        f'"{company_name}" about us',
        f'"{company_name}" business description',
        f'"{company_name}" what we do',
        f'"{company_name}" services',
        f'"{company_name}" products',
        f'"{company_name}" industry sector'
    ]
    
    # Add phone-based search if available
    if prospect_phone:
        industry_queries.append(f'"{company_name}" "{prospect_phone}"')
    
    # Add email domain search if available
    if prospect_email and '@' in prospect_email:
        email_domain = prospect_email.split('@')[1]
        industry_queries.append(f'"{company_name}" "{email_domain}"')
    
    all_results = []
    
    for query in industry_queries:
        print(f"      -> Industry detection query: {query}")
        
        # Add delay to avoid rate limiting
        sleep(random.uniform(1.5, 2.5))
        
        # Try DuckDuckGo first
        try:
            with DDGS() as ddgs:
                ddgs_results = list(ddgs.text(query, max_results=5))
                for result in ddgs_results:
                    all_results.append({
                        "source": "DuckDuckGo",
                        "query": query,
                        "title": result.get('title', 'N/A'),
                        "link": result.get('href', 'N/A'),
                        "snippet": result.get('body', 'N/A')
                    })
        except Exception as e:
            print(f"        [WARN] DuckDuckGo failed for industry detection: {e}")
        
        # Try Google as backup
        try:
            sleep(random.uniform(2.0, 3.0))
            google_results_gen = google_search(query, num_results=3, sleep_interval=2)
            for url in google_results_gen:
                all_results.append({
                    "source": "Google",
                    "query": query,
                    "title": "N/A (Google search)",
                    "link": url,
                    "snippet": "N/A (Google search)"
                })
        except Exception as e:
            print(f"        [WARN] Google search failed for industry detection: {e}")
    
    return all_results

def perform_enhanced_web_searches(company_name: str, prospect_name: str, industry: str = None, num_results: int = 5):
    """
    Performs comprehensive web searches using multiple strategies and sources.
    Prioritizes prospect-specific searches before falling back to broader company research.
    
    Args:
        company_name: The target company name
        prospect_name: The target prospect name
        industry: The industry the company operates in
        num_results: Number of results per query
    
    Returns:
        dict: Comprehensive intelligence report
    """
    print(f"  [ENRICH] Starting enhanced web searches for '{prospect_name} at {company_name}'...")
    
    intelligence_report = {
        "prospect_specific_intelligence": {},  # NEW: Prospect-specific results
        "company_intelligence": {},
        "industry_intelligence": {},
        "competitive_intelligence": {},
        "search_metadata": {
            "company_name": company_name,
            "prospect_name": prospect_name,
            "industry": industry,
            "total_queries": 0,
            "successful_searches": 0,
            "prospect_results_found": False
        }
    }
    
    total_queries = 0
    successful_searches = 0
    
    # --- PHASE 1: Prospect-Specific Searches (Primary Strategy) ---
    print("  [ENRICH] Phase 1: Prospect-specific searches (primary strategy)...")
    
    prospect_specific_queries = [
        f'"{prospect_name}" "{company_name}"',
        f'"{prospect_name}" "{company_name}" title role position',
        f'"{prospect_name}" "{company_name}" linkedin profile',
        f'"{prospect_name}" "{company_name}" executive management',
        f'"{prospect_name}" "{company_name}" professional background',
        f'"{prospect_name}" "{company_name}" career experience',
        f'"{prospect_name}" "{company_name}" business contact',
        f'"{prospect_name}" "{company_name}" email phone'
    ]
    
    prospect_results = []
    prospect_results_found = False
    
    for query in prospect_specific_queries:
        total_queries += 1
        print(f"    -> Prospect-specific query: {query}")
        
        # Add delay to avoid rate limiting
        delay = random.uniform(1.5, 2.5)
        sleep(delay)
        
        # Try DuckDuckGo first (more reliable)
        try:
            with DDGS() as ddgs:
                # Get more results for prospect searches to ensure we have enough
                ddgs_results = list(ddgs.text(query, max_results=10))
                for result in ddgs_results:
                    prospect_results.append({
                        "source": "DuckDuckGo",
                        "query": query,
                        "title": result.get('title', 'N/A'),
                        "link": result.get('href', 'N/A'),
                        "snippet": result.get('body', 'N/A'),
                        "timestamp": pd.Timestamp.now().isoformat(),
                        "search_type": "prospect_specific"
                    })
                successful_searches += 1
                print(f"      -> Found {len(ddgs_results)} DuckDuckGo results")
                
        except Exception as e:
            print(f"        [WARN] DuckDuckGo failed for '{query}': {e}")
        
        # Try Google as backup (with longer delay)
        try:
            sleep(random.uniform(2.0, 3.0))
            google_results_gen = google_search(query, num_results=10, sleep_interval=2)
            google_results = list(google_results_gen)
            for url in google_results:
                prospect_results.append({
                    "source": "Google",
                    "query": query,
                    "title": "N/A (Google search)",
                    "link": url,
                    "snippet": "N/A (Google search)",
                    "timestamp": pd.Timestamp.now().isoformat(),
                    "search_type": "prospect_specific"
                })
            successful_searches += 1
            print(f"      -> Found {len(google_results)} Google results")
            
        except Exception as e:
            print(f"        [WARN] Google search failed for '{query}': {e}")
    
    # Check if we found prospect-specific results
    if prospect_results:
        prospect_results_found = True
        intelligence_report["search_metadata"]["prospect_results_found"] = True
        print(f"  [ENRICH] ✅ Found {len(prospect_results)} prospect-specific results!")
        
        # Ensure we have at least 10 relevant results
        if len(prospect_results) < 10:
            print(f"  [ENRICH] ⚠️  Only found {len(prospect_results)} prospect results, need at least 10")
            # Additional targeted searches to get more results
            additional_queries = [
                f'"{prospect_name}" "{company_name}" contact information',
                f'"{prospect_name}" "{company_name}" professional history',
                f'"{prospect_name}" "{company_name}" business role',
                f'"{prospect_name}" "{company_name}" executive team'
            ]
            
            for query in additional_queries:
                total_queries += 1
                print(f"    -> Additional prospect query: {query}")
                sleep(random.uniform(1.5, 2.5))
                
                try:
                    with DDGS() as ddgs:
                        ddgs_results = list(ddgs.text(query, max_results=5))
                        for result in ddgs_results:
                            prospect_results.append({
                                "source": "DuckDuckGo",
                                "query": query,
                                "title": result.get('title', 'N/A'),
                                "link": result.get('href', 'N/A'),
                                "snippet": result.get('body', 'N/A'),
                                "timestamp": pd.Timestamp.now().isoformat(),
                                "search_type": "prospect_specific_additional"
                            })
                        successful_searches += 1
                        
                except Exception as e:
                    print(f"        [WARN] Additional DuckDuckGo search failed: {e}")
        
        # Store prospect-specific results
        intelligence_report["prospect_specific_intelligence"] = {
            "prospect_profile": prospect_results[:10],  # Top 10 most relevant
            "total_results": len(prospect_results),
            "search_strategy": "prospect_name_company_name_primary"
        }
        
        print(f"  [ENRICH] ✅ Prospect intelligence complete: {len(prospect_results)} total results")
    
    else:
        print(f"  [ENRICH] ❌ No prospect-specific results found, falling back to company research")
    
    # --- PHASE 2: Company Research (Fallback Strategy) ---
    print("  [ENRICH] Phase 2: Company research (fallback strategy)...")
    
    # Generate company search queries
    all_queries = generate_search_queries(company_name, prospect_name, industry)
    
    # Process each category of queries
    for category, query_groups in all_queries.items():
        if not query_groups:  # Skip empty industry queries
            continue
            
        intelligence_report[f"{category}_intelligence"] = {}
        
        for query_type, queries in query_groups.items():
            print(f"    -> Researching {category}: {query_type}")
            
            category_results = []
            
            for query in queries:
                total_queries += 1
                print(f"      -> Query: {query}")
                
                # Add intelligent delays to avoid rate limiting
                delay = random.uniform(1.5, 3.0)
                sleep(delay)
                
                # Try DuckDuckGo first (more reliable)
                try:
                    with DDGS() as ddgs:
                        ddgs_results = list(ddgs.text(query, max_results=num_results))
                        for result in ddgs_results:
                            category_results.append({
                                "source": "DuckDuckGo",
                                "query": query,
                                "title": result.get('title', 'N/A'),
                                "link": result.get('href', 'N/A'),
                                "snippet": result.get('body', 'N/A'),
                                "timestamp": pd.Timestamp.now().isoformat(),
                                "search_type": "company_research"
                            })
                        successful_searches += 1
                        
                except Exception as e:
                    print(f"        [WARN] DuckDuckGo failed for '{query}': {e}")
                
                # Try Google as backup (with longer delay)
                try:
                    sleep(random.uniform(2.0, 4.0))  # Longer delay for Google
                    google_results_gen = google_search(query, num_results=num_results, sleep_interval=2)
                    for url in google_results_gen:
                        category_results.append({
                            "source": "Google",
                            "query": query,
                            "title": "N/A (Google search)",
                            "link": url,
                            "snippet": "N/A (Google search)",
                            "timestamp": pd.Timestamp.now().isoformat(),
                            "search_type": "company_research"
                        })
                    successful_searches += 1
                    
                except Exception as e:
                    print(f"        [WARN] Google search failed for '{query}': {e}")
            
            # Store results for this query type
            intelligence_report[f"{category}_intelligence"][query_type] = category_results
    
    # Update metadata
    intelligence_report["search_metadata"]["total_queries"] = total_queries
    intelligence_report["search_metadata"]["successful_searches"] = successful_searches
    
    print(f"  [ENRICH] Completed {total_queries} queries with {successful_searches} successful searches")
    
    if prospect_results_found:
        print(f"  [ENRICH] 🎯 SUCCESS: Found prospect-specific intelligence with {len(prospect_results)} results")
        print(f"  [ENRICH] 📊 Strategy: Prospect + Company Name (Primary) + Company Research (Fallback)")
    else:
        print(f"  [ENRICH] 📊 Strategy: Company Research Only (No prospect-specific results found)")
    
    return intelligence_report

# --- Enhanced Orchestrator Function ---

def enrich_lead(lead_series: pd.Series):
    """
    Orchestrates the enhanced enrichment process with Gemini AI industry detection.
    
    Args:
        lead_series (pd.Series): A single row from the leads DataFrame.
    
    Returns:
        dict: A comprehensive intelligence report with detected industry.
    """
    prospect_name = lead_series.get('Prospect_Name', 'N/A')
    company_name = lead_series.get('Company_Name', 'N/A')
    prospect_phone = lead_series.get('Prospect_Phone', 'N/A')
    prospect_email = lead_series.get('Prospect_Email', 'N/A')
    
    print(f"\n--- Enhanced Enrichment with AI Industry Detection for Lead: {prospect_name} at {company_name} ---")
    
    if prospect_name == 'N/A' or company_name == 'N/A':
        print("  [ERROR] Lead is missing Prospect_Name or Company_Name. Skipping enrichment.")
        return {"error": "Missing critical lead information."}

    try:
        # Step 1: Industry Detection with Gemini AI
        print("  [ENRICH] Step 1: Detecting industry using Gemini AI...")
        industry_search_results = perform_industry_detection_search(company_name, prospect_phone, prospect_email)
        
        if industry_search_results:
            detected_industry = detect_industry_with_gemini(company_name, industry_search_results)
        else:
            detected_industry = "Unknown (No search results)"
        
        print(f"  [ENRICH] Industry detection complete: {detected_industry}")
        
        # Step 2: Comprehensive Research using detected industry
        print("  [ENRICH] Step 2: Performing comprehensive research...")
        intelligence_report = perform_enhanced_web_searches(company_name, prospect_name, detected_industry)
        
        # Add lead metadata including detected industry
        intelligence_report["lead_metadata"] = {
            "prospect_name": prospect_name,
            "company_name": company_name,
            "detected_industry": detected_industry,
            "prospect_phone": prospect_phone,
            "prospect_email": prospect_email,
            "enrichment_timestamp": pd.Timestamp.now().isoformat()
        }
        
        # Add industry detection results
        intelligence_report["industry_detection"] = {
            "detected_industry": detected_industry,
            "search_results_analyzed": len(industry_search_results),
            "detection_method": "Gemini AI analysis of search results"
        }
        
        print("--- Enhanced Enrichment with AI Industry Detection Complete ---")
        print(f"  -> Detected Industry: {detected_industry}")
        
        # Report on prospect-specific intelligence
        if intelligence_report.get("prospect_specific_intelligence"):
            prospect_data = intelligence_report["prospect_specific_intelligence"]
            print(f"  -> 🎯 Prospect-specific intelligence: {prospect_data.get('total_results', 0)} results found")
            print(f"  -> 📊 Search strategy: {prospect_data.get('search_strategy', 'Unknown')}")
        else:
            print(f"  -> ❌ No prospect-specific intelligence found")
        
        print(f"  -> Company intelligence: {len(intelligence_report.get('company_intelligence', {}))} categories")
        print(f"  -> Industry intelligence: {len(intelligence_report.get('industry_intelligence', {}))} categories")
        print(f"  -> Competitive intelligence: {len(intelligence_report.get('competitive_intelligence', {}))} categories")
        
        return intelligence_report

    except Exception as e:
        print(f"  [ERROR] An unexpected error occurred during enrichment: {e}")
        return {"error": str(e)}

