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

def perform_fast_industry_detection_search(company_name: str, prospect_phone: str = None, prospect_email: str = None):
    """
    Performs targeted searches to gather information for industry detection.
    Optimized for speed, reduces delays and results.
    
    Args:
        company_name: The company name
        prospect_phone: Phone number (optional)
        prospect_email: Email domain (optional)
    
    Returns:
        list: Search results for industry analysis
    """
    print(f"    -> Performing FAST industry detection search for: {company_name}")
    
    # Reduced query set for speed
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
        print(f"      -> FAST industry detection query: {query}")
        
        # OPTIMIZED: Reduced delays for speed
        delay = random.uniform(0.8, 1.2)  # Was 1.5-2.5
        sleep(delay)
        
        # Try DuckDuckGo first (more reliable)
        try:
            with DDGS() as ddgs:
                # OPTIMIZED: Reduced results for speed
                ddgs_results = list(ddgs.text(query, max_results=6))  # Was 10
                for result in ddgs_results:
                    all_results.append({
                        "source": "DuckDuckGo",
                        "query": query,
                        "title": result.get('title', 'N/A'),
                        "link": result.get('href', 'N/A'),
                        "snippet": result.get('body', 'N/A')
                    })
        except Exception as e:
            print(f"        [WARN] DuckDuckGo failed for FAST industry detection: {e}")
        
        # Try Google as backup (OPTIMIZED: faster delays)
        try:
            sleep(random.uniform(1.0, 1.5))  # Was 2.0-3.0
            google_results_gen = google_search(query, num_results=6, sleep_interval=1)  # Was 10, sleep_interval=2
            google_results = list(google_results_gen)
            for url in google_results:
                all_results.append({
                    "source": "Google",
                    "query": query,
                    "title": "N/A (Google search)",
                    "link": url,
                    "snippet": "N/A (Google search)"
                })
        except Exception as e:
            print(f"        [WARN] Google search failed for FAST industry detection: {e}")
    
    return all_results

def perform_enhanced_web_searches(company_name: str, prospect_name: str, industry: str = None, num_results: int = 5):
    """
    Performs comprehensive web searches using multiple strategies and sources.
    OPTIMIZED FOR SPEED: Target completion within 90 seconds.
    NEW FLOW: Prospect searches first → Industry detection → Company research with context.
    
    Args:
        company_name: The target company name
        prospect_name: The target prospect name
        industry: The industry the company operates in (optional, will be detected if not provided)
        num_results: Number of results per query
    
    Returns:
        dict: Comprehensive intelligence report
    """
    print(f"  [ENRICH] Starting OPTIMIZED web searches for '{prospect_name} at {company_name}'...")
    print(f"  [ENRICH] Target completion time: 90 seconds")
    
    intelligence_report = {
        "prospect_specific_intelligence": {},
        "company_intelligence": {},
        "industry_intelligence": {},
        "competitive_intelligence": {},
        "search_metadata": {
            "company_name": company_name,
            "prospect_name": prospect_name,
            "industry": industry,
            "total_queries": 0,
            "successful_searches": 0,
            "prospect_results_found": False,
            "industry_detected_from_prospect_results": False
        }
    }
    
    total_queries = 0
    successful_searches = 0
    
    try:
        # --- PHASE 1: FAST Prospect-Specific Searches (Primary Strategy) ---
        print("  [ENRICH] Phase 1: FAST prospect-specific searches (target: 45 seconds)...")
        
        # Reduced query set for speed - focus on most effective searches
        prospect_specific_queries = [
            f'"{prospect_name}" "{company_name}"',
            f'"{prospect_name}" "{company_name}" linkedin',
            f'"{prospect_name}" "{company_name}" title role',
            f'"{prospect_name}" "{company_name}" executive',
            f'"{prospect_name}" "{company_name}" contact'
        ]
        
        prospect_results = []
        prospect_results_found = False
        
        for query in prospect_specific_queries:
            total_queries += 1
            print(f"    -> FAST prospect query: {query}")
            
            # OPTIMIZED: Reduced delays for speed
            delay = random.uniform(0.8, 1.2)  # Was 1.5-2.5
            sleep(delay)
            
            # Try DuckDuckGo first (more reliable)
            try:
                with DDGS() as ddgs:
                    # OPTIMIZED: Reduced results for speed
                    ddgs_results = list(ddgs.text(query, max_results=20))  # Was 10
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
            
            # Try Google as backup (OPTIMIZED: faster delays)
            try:
                sleep(random.uniform(1.0, 1.5))  # Was 2.0-3.0
                google_results_gen = google_search(query, num_results=20, sleep_interval=1)  # Was 10, sleep_interval=2
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
            
            # OPTIMIZED: Only run additional searches if we have very few results
            if len(prospect_results) < 5:  # Was 10
                print(f"  [ENRICH] ⚠️  Only found {len(prospect_results)} prospect results, running 2 additional queries...")
                # Reduced additional queries for speed
                additional_queries = [
                    f'"{prospect_name}" "{company_name}" professional',
                    f'"{prospect_name}" "{company_name}" business'
                ]
                
                for query in additional_queries:
                    total_queries += 1
                    print(f"    -> Additional FAST query: {query}")
                    sleep(random.uniform(0.8, 1.2))  # OPTIMIZED: faster delays
                    
                    try:
                        with DDGS() as ddgs:
                            ddgs_results = list(ddgs.text(query, max_results=3))  # Was 5
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
                    
                    # Try Google for additional queries too (OPTIMIZED: faster)
                    try:
                        sleep(random.uniform(1.0, 1.5))  # Was 2.0-3.0
                        google_results_gen = google_search(query, num_results=3, sleep_interval=1)  # Was 5, sleep_interval=2
                        google_results = list(google_results_gen)
                        for url in google_results:
                            prospect_results.append({
                                "source": "Google",
                                "query": query,
                                "title": "N/A (Google search)",
                                "link": url,
                                "snippet": "N/A (Google search)",
                                "timestamp": pd.Timestamp.now().isoformat(),
                                "search_type": "prospect_specific_additional"
                            })
                        successful_searches += 1
                        
                    except Exception as e:
                        print(f"        [WARN] Additional Google search failed: {e}")
            
            # Store prospect-specific results
            intelligence_report["prospect_specific_intelligence"] = {
                "prospect_profile": prospect_results[:8],  # Top 8 most relevant (was 10)
                "total_results": len(prospect_results),
                "search_strategy": "prospect_name_company_name_primary_optimized"
            }
            
            print(f"  [ENRICH] ✅ Prospect intelligence complete: {len(prospect_results)} total results")
            print(f"  [ENRICH] 📊 Prospect results breakdown:")
            print(f"    -> Total results: {len(prospect_results)}")
            print(f"    -> DuckDuckGo results: {len([r for r in prospect_results if r['source'] == 'DuckDuckGo'])}")
            print(f"    -> Google results: {len([r for r in prospect_results if r['source'] == 'Google'])}")
        
        else:
            print(f"  [ENRICH] ❌ No prospect-specific results found")
        
        # --- PHASE 2: FAST Industry Detection from Prospect Results ---
        print("  [ENRICH] Phase 2: FAST industry detection (target: 15 seconds)...")
        
        detected_industry = industry  # Use provided industry if available
        
        if not detected_industry and prospect_results:
            print("  [ENRICH] Using prospect search results to detect industry...")
            print(f"  [ENRICH] Analyzing {len(prospect_results)} prospect results for industry context...")
            try:
                detected_industry = detect_industry_with_gemini(company_name, prospect_results)
                intelligence_report["search_metadata"]["industry_detected_from_prospect_results"] = True
                print(f"  [ENRICH] ✅ Industry detected from prospect results: {detected_industry}")
            except Exception as e:
                print(f"  [ERROR] Industry detection from prospect results failed: {e}")
                detected_industry = "Unknown (Detection failed)"
        
        elif not detected_industry and not prospect_results:
            print("  [ENRICH] No prospect results available, performing FAST basic industry detection...")
            try:
                # OPTIMIZED: Reduced industry detection queries for speed
                industry_search_results = perform_fast_industry_detection_search(company_name)
                if industry_search_results:
                    detected_industry = detect_industry_with_gemini(company_name, industry_search_results)
                else:
                    detected_industry = "Unknown (No search results)"
                print(f"  [ENRICH] Industry detection complete: {detected_industry}")
            except Exception as e:
                print(f"  [ERROR] Basic industry detection failed: {e}")
                detected_industry = "Unknown (Detection failed)"
        
        # Update the intelligence report with detected industry
        intelligence_report["search_metadata"]["industry"] = detected_industry
        
        # --- PHASE 3: FAST Company Research with Industry Context ---
        print("  [ENRICH] Phase 3: FAST company research (target: 30 seconds)...")
        
        # Generate company search queries using detected industry
        all_queries = generate_search_queries(company_name, prospect_name, detected_industry)
        
        # OPTIMIZED: Process only essential categories for speed
        essential_categories = ["company_overview", "industry_trends"]  # Focus on most important
        
        for category, query_groups in all_queries.items():
            if not query_groups:  # Skip empty industry queries
                continue
                
            intelligence_report[f"{category}_intelligence"] = {}
            
            for query_type, queries in query_groups.items():
                # OPTIMIZED: Skip non-essential queries for speed
                if category == "industry" and query_type not in essential_categories:
                    continue
                if category == "company" and query_type not in essential_categories:
                    continue
                
                print(f"    -> FAST researching {category}: {query_type}")
                
                category_results = []
                
                # OPTIMIZED: Process only first 2 queries per type for speed
                for query in queries[:2]:  # Was processing all queries
                    total_queries += 1
                    print(f"      -> FAST query: {query}")
                    
                    # OPTIMIZED: Faster delays for speed
                    delay = random.uniform(0.8, 1.5)  # Was 1.5-3.0
                    sleep(delay)
                    
                    # Try DuckDuckGo first (more reliable)
                    try:
                        with DDGS() as ddgs:
                            # OPTIMIZED: Reduced results for speed
                            ddgs_results = list(ddgs.text(query, max_results=3))  # Was num_results (5)
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
                    
                    # Try Google as backup (OPTIMIZED: faster delays)
                    try:
                        sleep(random.uniform(1.0, 2.0))  # Was 2.0-4.0
                        google_results_gen = google_search(query, num_results=3, sleep_interval=1)  # Was num_results, sleep_interval=2
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
        
        print(f"  [ENRICH] ✅ FAST search completed: {total_queries} queries with {successful_searches} successful searches")
        
        if prospect_results_found:
            print(f"  [ENRICH] 🎯 SUCCESS: Found prospect-specific intelligence with {len(prospect_results)} results")
            print(f"  [ENRICH] 📊 Strategy: FAST Prospect + Company Name → Industry Detection → Company Research")
        else:
            print(f"  [ENRICH] 📊 Strategy: FAST Company Research Only (No prospect-specific results found)")
        
        return intelligence_report
        
    except Exception as e:
        print(f"  [ERROR] Critical error in perform_enhanced_web_searches: {e}")
        # Return partial results if available
        intelligence_report["error"] = str(e)
        intelligence_report["search_metadata"]["error"] = str(e)
        return intelligence_report

# --- Enhanced Orchestrator Function ---

def enrich_lead(lead_series: pd.Series):
    """
    Orchestrates the enhanced enrichment process with integrated industry detection.
    NEW FLOW: Prospect searches → Industry detection → Company research with context.
    
    Args:
        lead_series (pd.Series): A single row from the leads DataFrame.
    
    Returns:
        dict: A comprehensive intelligence report with detected industry.
    """
    prospect_name = lead_series.get('Prospect_Name', 'N/A')
    company_name = lead_series.get('Company_Name', 'N/A')
    prospect_phone = lead_series.get('Prospect_Phone', 'N/A')
    prospect_email = lead_series.get('Prospect_Email', 'N/A')
    
    print(f"\n--- Enhanced Enrichment with Integrated Industry Detection for Lead: {prospect_name} at {company_name} ---")
    
    if prospect_name == 'N/A' or company_name == 'N/A':
        print("  [ERROR] Lead is missing Prospect_Name or Company_Name. Skipping enrichment.")
        return {"error": "Missing critical lead information."}

    try:
        # NEW FLOW: All-in-one enhanced search with integrated industry detection
        print("  [ENRICH] Starting integrated enrichment process...")
        intelligence_report = perform_enhanced_web_searches(company_name, prospect_name)
        
        # Add lead metadata
        intelligence_report["lead_metadata"] = {
            "prospect_name": prospect_name,
            "company_name": company_name,
            "detected_industry": intelligence_report["search_metadata"].get("industry", "Unknown"),
            "prospect_phone": prospect_phone,
            "prospect_email": prospect_email,
            "enrichment_timestamp": pd.Timestamp.now().isoformat()
        }
        
        # Add industry detection results
        intelligence_report["industry_detection"] = {
            "detected_industry": intelligence_report["search_metadata"].get("industry", "Unknown"),
            "detection_method": "Integrated with prospect search results",
            "detected_from_prospect_results": intelligence_report["search_metadata"].get("industry_detected_from_prospect_results", False)
        }
        
        print("--- Enhanced Enrichment with Integrated Industry Detection Complete ---")
        print(f"  -> Detected Industry: {intelligence_report['search_metadata'].get('industry', 'Unknown')}")
        
        # Report on prospect-specific intelligence
        if intelligence_report.get("prospect_specific_intelligence"):
            prospect_data = intelligence_report["prospect_specific_intelligence"]
            print(f"  -> 🎯 Prospect-specific intelligence: {prospect_data.get('total_results', 0)} results found")
            print(f"  -> 📊 Search strategy: {prospect_data.get('search_strategy', 'Unknown')}")
        else:
            print(f"  -> ❌ No prospect-specific intelligence found")
        
        # Report on industry detection method
        if intelligence_report["search_metadata"].get("industry_detected_from_prospect_results"):
            print(f"  -> 🎯 Industry detected from prospect search results")
        else:
            print(f"  -> 📊 Industry detected from basic company searches")
        
        print(f"  -> Company intelligence: {len(intelligence_report.get('company_intelligence', {}))} categories")
        print(f"  -> Industry intelligence: {len(intelligence_report.get('industry_intelligence', {}))} categories")
        print(f"  -> Competitive intelligence: {len(intelligence_report.get('competitive_intelligence', {}))} categories")
        
        return intelligence_report

    except Exception as e:
        print(f"  [ERROR] An unexpected error occurred during enrichment: {e}")
        return {"error": str(e)}

