from bs4 import BeautifulSoup
import json
import csv
import re
from datetime import datetime
import os

class EnhancedOLXParser:
    def __init__(self, html_file_path):
        self.html_file_path = html_file_path
        
    def analyze_html_structure(self):
        """Analyze the HTML structure to understand the page layout"""
        try:
            with open(self.html_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            soup = BeautifulSoup(content, 'html.parser')
            
            print("="*60)
            print("HTML STRUCTURE ANALYSIS")
            print("="*60)
            
            # Basic page info
            title = soup.find('title')
            print(f"Page Title: {title.text if title else 'Not found'}")
            
            # Check for common OLX indicators
            olx_indicators = [
                'olx', 'item', 'listing', 'product', 'ad', 'classified'
            ]
            
            found_indicators = []
            for indicator in olx_indicators:
                elements = soup.find_all(class_=lambda x: x and indicator in x.lower())
                if elements:
                    found_indicators.append(f"{indicator}: {len(elements)} elements")
            
            print(f"OLX-related elements found: {', '.join(found_indicators) if found_indicators else 'None'}")
            
            data_elements = soup.find_all(attrs={'data-aut-id': True})
            print(f"Elements with data-aut-id: {len(data_elements)}")
            
            if data_elements:
                unique_data_ids = set([elem.get('data-aut-id') for elem in data_elements])
                print("Common data-aut-id values:")
                for data_id in sorted(unique_data_ids)[:10]:  # Show first 10
                    print(f"  - {data_id}")
            
            # Look for price patterns
            price_patterns = [r'₹\s*[\d,]+', r'Rs\.?\s*[\d,]+', r'\d+\s*rupees?']
            prices_found = []
            for pattern in price_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                prices_found.extend(matches[:5])  # Limit to 5 examples
            
            print(f"Price patterns found: {prices_found[:10] if prices_found else 'None'}")
            
            all_links = soup.find_all('a', href=True)
            item_links = [link for link in all_links if any(keyword in link.get('href', '').lower() 
                                                           for keyword in ['item', 'ad', 'product', 'listing'])]
            print(f"Potential listing links: {len(item_links)}")
            
            # Check for JSON-LD or script data
            scripts = soup.find_all('script')
            json_scripts = [script for script in scripts if script.string and 
                           any(keyword in script.string for keyword in ['json', 'item', 'product'])]
            print(f"Potential JSON data scripts: {len(json_scripts)}")
            
            # Look for common container patterns
            container_patterns = ['container', 'wrapper', 'main', 'content', 'list', 'grid']
            containers = []
            for pattern in container_patterns:
                elements = soup.find_all(class_=lambda x: x and pattern in x.lower())
                if elements:
                    containers.append(f"{pattern}: {len(elements)}")
            print(f"Container elements: {', '.join(containers) if containers else 'None'}")
            
            return soup
            
        except Exception as e:
            print(f"Error analyzing HTML structure: {e}")
            return None
    
    def extract_from_json_scripts(self, soup):
        """Try to extract data from JSON scripts embedded in the page"""
        listings = []
        
        scripts = soup.find_all('script')
        for script in scripts:
            if not script.string:
                continue
                
            script_content = script.string.strip()
            
            # Look for JSON patterns that might contain listing data
            json_patterns = [
                r'window\.__INITIAL_STATE__\s*=\s*({.+?});',
                r'window\.__APOLLO_STATE__\s*=\s*({.+?});',
                r'__NEXT_DATA__\s*=\s*({.+?})',
                r'window\.initialState\s*=\s*({.+?});'
            ]
            
            for pattern in json_patterns:
                matches = re.findall(pattern, script_content, re.DOTALL)
                for match in matches:
                    try:
                        data = json.loads(match)
                        # Recursively search for listing-like data
                        found_listings = self.search_json_for_listings(data)
                        listings.extend(found_listings)
                    except:
                        continue
        
        return listings
    
    def search_json_for_listings(self, data, depth=0):
        """Recursively search JSON data for listing information"""
        if depth > 3:  # Prevent infinite recursion
            return []
        
        listings = []
        
        if isinstance(data, dict):
            # Look for keys that suggest listing data
            listing_keys = ['title', 'price', 'location', 'description', 'name']
            if any(key in data for key in listing_keys):
                # This might be a listing
                listing = {
                    'title': data.get('title', data.get('name', 'N/A')),
                    'price': str(data.get('price', data.get('amount', 'N/A'))),
                    'location': data.get('location', data.get('city', 'N/A')),
                    'date': data.get('date', data.get('createdAt', 'N/A')),
                    'link': data.get('url', data.get('link', 'N/A')),
                    'image_url': data.get('image', data.get('thumbnail', 'N/A')),
                    'seller': 'N/A'
                }
                if listing['title'] != 'N/A':
                    listings.append(listing)
            
            # Continue searching in nested objects
            for value in data.values():
                listings.extend(self.search_json_for_listings(value, depth + 1))
                
        elif isinstance(data, list):
            for item in data:
                listings.extend(self.search_json_for_listings(item, depth + 1))
        
        return listings
    
    def extract_with_flexible_selectors(self, soup):
        """Try multiple selector strategies to find listings"""
        listings = []
        
        # Strategy 1: OLX-specific selectors
        selectors_v1 = [
            {'data-aut-id': 'itemBox'},
            {'class_': lambda x: x and 'item' in x.lower()},
            {'class_': lambda x: x and 'listing' in x.lower()},
            {'class_': lambda x: x and 'ad' in x.lower()},
        ]
        
        for selector in selectors_v1:
            elements = soup.find_all('div', selector)
            if elements:
                print(f"Found {len(elements)} elements with selector: {selector}")
                for elem in elements:
                    data = self.extract_from_element(elem)
                    if data and data.get('title', 'N/A') != 'N/A':
                        listings.append(data)
                break
        
        # Strategy 2: Look for repeated patterns
        if not listings:
            # Find elements that repeat frequently (likely listings)
            all_divs = soup.find_all('div')
            class_counts = {}
            
            for div in all_divs:
                classes = div.get('class', [])
                for cls in classes:
                    class_counts[cls] = class_counts.get(cls, 0) + 1
            
            # Find classes that appear multiple times (likely listing containers)
            frequent_classes = [cls for cls, count in class_counts.items() if count >= 3]
            
            for cls in frequent_classes[:5]:  # Try top 5 most frequent classes
                elements = soup.find_all('div', class_=cls)
                if len(elements) >= 3:  # Must have at least 3 elements
                    print(f"Trying frequent class: {cls} ({len(elements)} elements)")
                    temp_listings = []
                    for elem in elements[:10]:  # Test first 10
                        data = self.extract_from_element(elem)
                        if data and data.get('title', 'N/A') != 'N/A':
                            temp_listings.append(data)
                    
                    if len(temp_listings) >= 2:  # If we found at least 2 valid listings
                        listings.extend(temp_listings)
                        break
        
        # Strategy 3: Look for links with item/ad patterns
        if not listings:
            item_links = soup.find_all('a', href=lambda x: x and any(
                keyword in x.lower() for keyword in ['item', 'ad', 'product']))
            
            print(f"Found {len(item_links)} potential item links")
            for link in item_links[:20]:  # Process first 20 links
                # Get the parent container
                parent = link.find_parent(['div', 'li', 'article'])
                if parent:
                    data = self.extract_from_element(parent)
                    if data and data.get('title', 'N/A') != 'N/A':
                        listings.append(data)
        
        return listings
    
    def extract_from_element(self, element):
        """Extract listing data from a single element using multiple strategies"""
        try:
            data = {}
            
            # Title extraction strategies
            title_selectors = [
                '[data-aut-id="itemTitle"]',
                'h1', 'h2', 'h3', 'h4',
                '.title', '.name', '.heading',
                'a[href*="item"]'
            ]
            
            data['title'] = self.find_text_by_selectors(element, title_selectors)
            
            # Price extraction
            price_selectors = [
                '[data-aut-id="itemPrice"]',
                '.price', '.amount', '.cost',
                '*[class*="price"]', '*[id*="price"]'
            ]
            
            price_text = self.find_text_by_selectors(element, price_selectors)
            if price_text == 'N/A':
                # Look for price patterns in text
                text = element.get_text()
                price_match = re.search(r'₹\s*[\d,]+|Rs\.?\s*[\d,]+', text)
                price_text = price_match.group() if price_match else 'N/A'
            
            data['price'] = price_text
            
            # Location extraction
            location_selectors = [
                '[data-aut-id="item-location"]',
                '.location', '.place', '.city',
                '*[class*="location"]', '*[class*="place"]'
            ]
            
            data['location'] = self.find_text_by_selectors(element, location_selectors)
            
            # Date extraction
            date_selectors = [
                '[data-aut-id="item-date"]',
                '.date', '.time', '.posted',
                '*[class*="date"]', '*[class*="time"]'
            ]
            
            data['date'] = self.find_text_by_selectors(element, date_selectors)
            
            # Link extraction
            link_elem = element.find('a', href=True)
            if link_elem:
                href = link_elem.get('href')
                if href.startswith('/'):
                    data['link'] = f"https://www.olx.in{href}"
                else:
                    data['link'] = href
            else:
                data['link'] = 'N/A'
            
            # Image extraction
            img_elem = element.find('img')
            data['image_url'] = img_elem.get('src', 'N/A') if img_elem else 'N/A'
            
            data['seller'] = 'N/A'
            
            return data
            
        except Exception as e:
            return None
    
    def find_text_by_selectors(self, element, selectors):
        """Try multiple CSS selectors to find text"""
        for selector in selectors:
            try:
                found = element.select_one(selector)
                if found and found.get_text(strip=True):
                    return found.get_text(strip=True)
            except:
                continue
        return 'N/A'
    
    def parse_html_file(self):
        """Main parsing function with comprehensive strategies"""
        print(f"Parsing HTML file: {self.html_file_path}")
        
        soup = self.analyze_html_structure()
        if not soup:
            return []
        
        all_listings = []
        
        # Strategy 1: Try to extract from JSON scripts
        print("\n1. Trying JSON script extraction...")
        json_listings = self.extract_from_json_scripts(soup)
        if json_listings:
            print(f"Found {len(json_listings)} listings from JSON data")
            all_listings.extend(json_listings)
        
        # Strategy 2: Try flexible HTML selectors
        print("\n2. Trying flexible HTML selectors...")
        html_listings = self.extract_with_flexible_selectors(soup)
        if html_listings:
            print(f"Found {len(html_listings)} listings from HTML parsing")
            all_listings.extend(html_listings)
        
        # Remove duplicates based on title
        seen_titles = set()
        unique_listings = []
        for listing in all_listings:
            title = listing.get('title', '').lower()
            if title and title != 'n/a' and title not in seen_titles:
                seen_titles.add(title)
                unique_listings.append(listing)
        
        return unique_listings
    
    def save_results(self, listings):
        """Save results to files"""
        if not listings:
            print("No listings to save")
            return
        
        # Save to JSON
        json_filename = 'olx_enhanced_parsing.json'
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump({
                'search_query': 'car cover',
                'scraped_at': datetime.now().isoformat(),
                'total_listings': len(listings),
                'method': 'enhanced_html_parsing',
                'source_file': self.html_file_path,
                'listings': listings
            }, f, indent=2, ensure_ascii=False)
        
        # Save to CSV
        csv_filename = 'olx_enhanced_parsing.csv'
        fieldnames = ['title', 'price', 'location', 'date', 'link', 'image_url', 'seller']
        
        with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(listings)
        
        print(f"\nResults saved:")
        print(f"- JSON: {json_filename}")
        print(f"- CSV: {csv_filename}")
        
        # Print summary
        print(f"\n{'='*50}")
        print(f"ENHANCED PARSING SUMMARY")
        print(f"{'='*50}")
        print(f"Total unique listings: {len(listings)}")
        print(f"Source file: {self.html_file_path}")
        
        if listings:
            print(f"\nSample listings:")
            for i, listing in enumerate(listings[:5], 1):
                print(f"\n{i}. {listing['title']}")
                print(f"   Price: {listing['price']}")
                print(f"   Location: {listing['location']}")

def main():
    print("Enhanced OLX HTML Parser")
    print("="*40)
    print("This parser can handle various OLX page structures")
    print("and includes debugging features.\n")
    
    html_file = input("Enter HTML file path (default: olx_page.html): ").strip()
    if not html_file:
        html_file = "olx_page.html"
    
    if not os.path.exists(html_file):
        print(f"\nFile '{html_file}' not found!")
        print("\nTo create the HTML file:")
        print("1. Go to https://www.olx.in/items/q-car-cover")
        print("2. Wait for the page to fully load (scroll down if needed)")
        print("3. Right-click → 'Save as' → save as 'olx_page.html'")
        print("4. Make sure to save as 'Webpage, Complete' if given options")
        return
    
    parser = EnhancedOLXParser(html_file)
    listings = parser.parse_html_file()
    
    if listings:
        parser.save_results(listings)
    else:
        print("\nNo listings found. This could mean:")
        print("1. The page uses heavy JavaScript (try saving after scrolling)")
        print("2. OLX changed their HTML structure")
        print("3. The page didn't load completely when saved")
        print("\nTry:")
        print("- Save the page again after fully loading")
        print("- Scroll down to load more items before saving")
        print("- Try a different browser to save the page")

if __name__ == "__main__":
    main()

# For manual comprehensive scraping instructions

'''from bs4 import BeautifulSoup
import json
import csv
import re
import os
from datetime import datetime
import requests
from urllib.parse import urljoin, urlparse

class ManualComprehensiveScraper:
    def __init__(self):
        self.base_url = "https://www.olx.in"
        self.all_listings = []
        
    def get_detailed_instructions(self):
        """Provide detailed instructions for manual comprehensive scraping"""
        print("="*70)
        print("MANUAL COMPREHENSIVE SCRAPING INSTRUCTIONS")
        print("="*70)
        print("\n🎯 GOAL: Get ALL listings (200-1000+) from OLX search results")
        print("\n📋 STEP-BY-STEP PROCESS:")
        print("\n1. 🌐 OPEN YOUR BROWSER")
        print("   - Use Chrome, Firefox, Edge, or any browser")
        print("   - Go to: https://www.olx.in/items/q-car-cover")
        
        print("\n2. 🔄 LOAD ALL CONTENT (MOST IMPORTANT STEP)")
        print("   - Wait for the page to fully load (5-10 seconds)")
        print("   - Scroll down SLOWLY - this loads more listings")
        print("   - Keep scrolling until you see 'No more results' or similar")
        print("   - This may take 5-10 minutes of scrolling")
        print("   - You should see hundreds of listings load")
        
        print("\n3. 💾 SAVE THE COMPLETE PAGE")
        print("   - Press Ctrl+S (Windows) or Cmd+S (Mac)")
        print("   - Choose 'Webpage, Complete' (important!)")
        print("   - Save as: olx_complete.html")
        print("   - Save in the same folder as this Python script")
        
        print("\n4. 🚀 RUN THE PARSER")
        print("   - Run this script")
        print("   - It will parse your comprehensive HTML file")
        print("   - Extract ALL listings you loaded")
        
        print("\n⚠️  CRITICAL TIPS FOR MAXIMUM LISTINGS:")
        print("   - Don't rush the scrolling - let content load")
        print("   - Scroll in small increments, not big jumps")
        print("   - Wait 2-3 seconds between scrolls")
        print("   - Look for 'Load More' buttons and click them")
        print("   - The more you scroll, the more listings you'll get")
        
        print("\n📊 EXPECTED RESULTS:")
        print("   - Quick scroll: ~50 listings")
        print("   - Moderate scroll: ~200 listings") 
        print("   - Full scroll: 500-1000+ listings")
        print("\n" + "="*70)
    
    def analyze_html_comprehensively(self, html_file):
        """Comprehensive analysis of the HTML file"""
        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            soup = BeautifulSoup(content, 'html.parser')
            
            print(f"\n{'='*60}")
            print("COMPREHENSIVE HTML ANALYSIS")
            print(f"{'='*60}")
            
            # File size analysis
            file_size = len(content) / (1024 * 1024)  # MB
            print(f"HTML file size: {file_size:.2f} MB")
            
            if file_size < 0.5:
                print("⚠️  WARNING: File seems small. You may need to scroll more to load all content.")
            elif file_size > 2:
                print("✅ Good file size - likely contains many listings!")
            
            # Title analysis
            title = soup.find('title')
            print(f"Page title: {title.text if title else 'Not found'}")
            
            # Count potential listings using multiple methods
            analysis_results = {}
            
            # Method 1: Data attributes
            data_elements = soup.find_all(attrs={'data-aut-id': True})
            item_boxes = [elem for elem in data_elements if 'item' in elem.get('data-aut-id', '').lower()]
            analysis_results['data_item_boxes'] = len(item_boxes)
            
            # Method 2: Links with 'item' in href
            all_links = soup.find_all('a', href=True)
            item_links = [link for link in all_links if 'item' in link.get('href', '')]
            analysis_results['item_links'] = len(item_links)
            
            # Method 3: Price patterns
            price_patterns = re.findall(r'₹\s*[\d,]+', content)
            analysis_results['price_mentions'] = len(set(price_patterns))
            
            # Method 4: Repeated class patterns
            all_divs = soup.find_all('div', class_=True)
            class_counts = {}
            for div in all_divs:
                classes = div.get('class', [])
                for cls in classes:
                    if len(cls) > 3:  # Ignore very short classes
                        class_counts[cls] = class_counts.get(cls, 0) + 1
            
            # Find most frequent classes (likely listing containers)
            frequent_classes = [(cls, count) for cls, count in class_counts.items() 
                              if count >= 10 and count <= 1000]  # Reasonable range
            frequent_classes.sort(key=lambda x: x[1], reverse=True)
            
            print(f"\nPotential listing indicators:")
            for method, count in analysis_results.items():
                print(f"  {method}: {count}")
            
            if frequent_classes:
                print(f"\nTop frequent classes (potential listing containers):")
                for cls, count in frequent_classes[:5]:
                    print(f"  {cls}: {count} elements")
            
            # Estimate total listings
            estimates = [v for v in analysis_results.values() if v > 0]
            if estimates:
                estimated_listings = max(estimates)
                print(f"\n📊 ESTIMATED LISTINGS: ~{estimated_listings}")
                
                if estimated_listings < 50:
                    print("⚠️  Recommendation: Scroll more and re-save the page for more listings")
                elif estimated_listings < 200:
                    print("✅ Good amount of listings!")
                else:
                    print("🎉 Excellent! Lots of listings to extract!")
            
            return soup, frequent_classes
            
        except Exception as e:
            print(f"Error analyzing HTML: {e}")
            return None, []
    
    def extract_with_multiple_strategies(self, soup, frequent_classes):
        """Use multiple extraction strategies to get maximum listings"""
        all_listings = []
        
        print(f"\n{'='*60}")
        print("EXTRACTION STRATEGIES")
        print(f"{'='*60}")
        
        # Strategy 1: OLX-specific data attributes
        print("\n1. Trying OLX-specific selectors...")
        olx_selectors = [
            {'data-aut-id': 'itemBox'},
            {'data-aut-id': lambda x: x and 'item' in x.lower()}
        ]
        
        for selector in olx_selectors:
            elements = soup.find_all('div', selector)
            if elements:
                print(f"   Found {len(elements)} elements with {selector}")
                for elem in elements:
                    data = self.extract_listing_data(elem)
                    if data and self.is_valid_listing(data):
                        all_listings.append(data)
                break
        
        # Strategy 2: Use frequent classes
        if not all_listings and frequent_classes:
            print("\n2. Trying frequent class patterns...")
            for cls, count in frequent_classes[:3]:  # Try top 3 frequent classes
                elements = soup.find_all('div', class_=cls)
                test_listings = []
                
                for elem in elements[:min(10, len(elements))]:  # Test first 10
                    data = self.extract_listing_data(elem)
                    if data and self.is_valid_listing(data):
                        test_listings.append(data)
                
                # If we get valid listings from >30% of elements, use this class
                if len(test_listings) > count * 0.3:
                    print(f"   Using class '{cls}': {len(elements)} elements")
                    for elem in elements:
                        data = self.extract_listing_data(elem)
                        if data and self.is_valid_listing(data):
                            all_listings.append(data)
                    break
        
        # Strategy 3: Item links approach
        if not all_listings:
            print("\n3. Trying item links approach...")
            all_links = soup.find_all('a', href=True)
            item_links = [link for link in all_links if 'item' in link.get('href', '')]
            
            print(f"   Found {len(item_links)} potential item links")
            processed_parents = set()
            
            for link in item_links:
                # Get parent container
                parent = link.find_parent(['div', 'li', 'article'])
                if parent and str(parent) not in processed_parents:
                    processed_parents.add(str(parent))
                    data = self.extract_listing_data(parent)
                    if data and self.is_valid_listing(data):
                        all_listings.append(data)
        
        # Strategy 4: JSON extraction
        print(f"\n4. Trying JSON script extraction...")
        json_listings = self.extract_from_json_scripts(soup)
        if json_listings:
            print(f"   Found {len(json_listings)} listings from JSON")
            all_listings.extend(json_listings)
        
        return all_listings
    
    def extract_listing_data(self, element):
        """Extract listing data from a soup element"""
        try:
            data = {}
            
            # Title extraction with multiple selectors
            title_selectors = [
                '[data-aut-id="itemTitle"]',
                'h1, h2, h3, h4, h5',
                'a[href*="item"]',
                '.title, .name, .heading'
            ]
            
            title = None
            for selector in title_selectors:
                try:
                    title_elem = element.select_one(selector)
                    if title_elem and title_elem.get_text(strip=True):
                        title = title_elem.get_text(strip=True)
                        break
                except:
                    continue
            
            data['title'] = title or 'N/A'
            
            # Price extraction
            price_selectors = [
                '[data-aut-id="itemPrice"]',
                '.price, .amount, .cost',
                '*[class*="price"]'
            ]
            
            price = None
            for selector in price_selectors:
                try:
                    price_elem = element.select_one(selector)
                    if price_elem and price_elem.get_text(strip=True):
                        price = price_elem.get_text(strip=True)
                        break
                except:
                    continue
            
            # If no price found, look for price patterns in text
            if not price:
                text = element.get_text()
                price_match = re.search(r'₹\s*[\d,]+', text)
                price = price_match.group() if price_match else 'N/A'
            
            data['price'] = price or 'N/A'
            
            # Location extraction
            location_selectors = [
                '[data-aut-id="item-location"]',
                '.location, .place, .city',
                '*[class*="location"]'
            ]
            
            location = None
            for selector in location_selectors:
                try:
                    loc_elem = element.select_one(selector)
                    if loc_elem and loc_elem.get_text(strip=True):
                        location = loc_elem.get_text(strip=True)
                        break
                except:
                    continue
            
            data['location'] = location or 'N/A'
            
            # Date extraction
            date_selectors = [
                '[data-aut-id="item-date"]',
                '.date, .time, .posted',
                '*[class*="date"]'
            ]
            
            date = None
            for selector in date_selectors:
                try:
                    date_elem = element.select_one(selector)
                    if date_elem and date_elem.get_text(strip=True):
                        date = date_elem.get_text(strip=True)
                        break
                except:
                    continue
            
            data['date'] = date or 'N/A'
            
            # Link extraction
            link_elem = element.find('a', href=True)
            if link_elem:
                href = link_elem.get('href')
                if href.startswith('/'):
                    data['link'] = f"{self.base_url}{href}"
                else:
                    data['link'] = href
            else:
                data['link'] = 'N/A'
            
            # Image extraction
            img_elem = element.find('img', src=True)
            data['image_url'] = img_elem.get('src') if img_elem else 'N/A'
            
            data['seller'] = 'N/A'
            
            return data
            
        except Exception as e:
            return None
    
    def extract_from_json_scripts(self, soup):
        """Extract data from JSON scripts in the page"""
        listings = []
        scripts = soup.find_all('script')
        
        for script in scripts:
            if not script.string:
                continue
            
            script_content = script.string.strip()
            
            # Look for JSON patterns
            json_patterns = [
                r'window\.__INITIAL_STATE__\s*=\s*({.+?});',
                r'window\.__APOLLO_STATE__\s*=\s*({.+?});',
                r'__NEXT_DATA__\s*=\s*({.+?})'
            ]
            
            for pattern in json_patterns:
                matches = re.findall(pattern, script_content, re.DOTALL)
                for match in matches:
                    try:
                        data = json.loads(match)
                        found_listings = self.search_json_for_listings(data)
                        listings.extend(found_listings)
                    except:
                        continue
        
        return listings
    
    def search_json_for_listings(self, data, depth=0):
        """Search JSON data for listings"""
        if depth > 3:
            return []
        
        listings = []
        
        if isinstance(data, dict):
            # Check if this looks like a listing
            listing_indicators = ['title', 'price', 'location', 'description']
            if any(key in data for key in listing_indicators):
                listing = {
                    'title': data.get('title', data.get('name', 'N/A')),
                    'price': str(data.get('price', data.get('amount', 'N/A'))),
                    'location': data.get('location', data.get('city', 'N/A')),
                    'date': data.get('date', data.get('createdAt', 'N/A')),
                    'link': data.get('url', data.get('link', 'N/A')),
                    'image_url': data.get('image', data.get('thumbnail', 'N/A')),
                    'seller': 'N/A'
                }
                if listing['title'] != 'N/A' and len(listing['title']) > 5:
                    listings.append(listing)
            
            # Continue searching nested objects
            for value in data.values():
                listings.extend(self.search_json_for_listings(value, depth + 1))
                
        elif isinstance(data, list):
            for item in data:
                listings.extend(self.search_json_for_listings(item, depth + 1))
        
        return listings
    
    def is_valid_listing(self, listing):
        """Check if a listing is valid"""
        title = listing.get('title', '').lower().strip()
        
        # Must have meaningful title
        if not title or title == 'n/a' or len(title) < 5:
            return False
        
        # Filter out navigation and category elements
        invalid_keywords = [
            'all categories', 'browse categories', 'home', 'login', 'register',
            'post ad', 'sell', 'buy', 'help', 'about', 'contact', 'privacy',
            'terms', 'policy', 'support', 'careers', 'blog', 'app download'
        ]
        
        return not any(keyword in title for keyword in invalid_keywords)
    
    def remove_duplicates(self, listings):
        """Remove duplicate listings"""
        unique_listings = []
        seen_titles = set()
        
        for listing in listings:
            title = listing.get('title', '').lower().strip()
            # Create a more flexible duplicate check
            title_key = ''.join(title.split()[:5])  # First 5 words
            
            if title_key and title_key not in seen_titles:
                seen_titles.add(title_key)
                unique_listings.append(listing)
        
        return unique_listings
    
    def save_comprehensive_results(self, listings):
        """Save the comprehensive results"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save to JSON
        json_filename = f'olx_manual_comprehensive_{timestamp}.json'
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump({
                'search_query': 'car cover (comprehensive manual scraping)',
                'scraped_at': datetime.now().isoformat(),
                'total_listings': len(listings),
                'method': 'manual_comprehensive_scraping',
                'listings': listings
            }, f, indent=2, ensure_ascii=False)
        
        # Save to CSV
        csv_filename = f'olx_manual_comprehensive_{timestamp}.csv'
        if listings:
            fieldnames = ['title', 'price', 'location', 'date', 'link', 'image_url', 'seller']
            with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(listings)
        
        print(f"\n✅ COMPREHENSIVE RESULTS SAVED:")
        print(f"📄 JSON: {json_filename}")
        print(f"📊 CSV: {csv_filename}")
        
        return json_filename, csv_filename
    
    def print_comprehensive_summary(self, listings):
        """Print comprehensive summary"""
        print(f"\n{'='*70}")
        print("COMPREHENSIVE SCRAPING SUMMARY")
        print(f"{'='*70}")
        print(f"Total listings extracted: {len(listings)}")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if not listings:
            print("\n❌ No listings found. Possible issues:")
            print("   - HTML file may not contain loaded listings")
            print("   - Page may not have been scrolled enough")
            print("   - OLX structure may have changed")
            return
        
        # Analyze the results
        prices = []
        locations = {}
        
        for listing in listings:
            # Extract price numbers
            price = listing.get('price', '')
            if price != 'N/A':
                price_nums = re.findall(r'[\d,]+', price.replace('₹', '').replace('Rs', ''))
                if price_nums:
                    try:
                        prices.append(int(price_nums[0].replace(',', '')))
                    except:
                        pass
            
            # Count locations
            location = listing.get('location', 'Unknown')
            if location != 'N/A':
                locations[location] = locations.get(location, 0) + 1
        
        if prices:
            print(f"\n💰 PRICE ANALYSIS:")
            print(f"   Range: ₹{min(prices):,} - ₹{max(prices):,}")
            print(f"   Average: ₹{sum(prices)//len(prices):,}")
            print(f"   Listings with prices: {len(prices)}")
        
        if locations:
            print(f"\n📍 TOP LOCATIONS:")
            sorted_locations = sorted(locations.items(), key=lambda x: x[1], reverse=True)
            for location, count in sorted_locations[:5]:
                print(f"   {location}: {count} listings")
        
        print(f"\n📋 SAMPLE LISTINGS:")
        for i, listing in enumerate(listings[:10], 1):
            print(f"\n{i}. {listing.get('title', 'N/A')}")
            print(f"   💰 Price: {listing.get('price', 'N/A')}")
            print(f"   📍 Location: {listing.get('location', 'N/A')}")
    
    def process_html_file(self, html_file):
        """Main processing function"""
        if not os.path.exists(html_file):
            print(f"\n❌ File '{html_file}' not found!")
            return []
        
        print(f"\n🔍 Processing: {html_file}")
        
        # Comprehensive analysis
        soup, frequent_classes = self.analyze_html_comprehensively(html_file)
        if not soup:
            return []
        
        # Extract listings using multiple strategies
        all_listings = self.extract_with_multiple_strategies(soup, frequent_classes)
        
        # Remove duplicates
        unique_listings = self.remove_duplicates(all_listings)
        
        print(f"\n📊 EXTRACTION RESULTS:")
        print(f"   Total extracted: {len(all_listings)}")
        print(f"   After removing duplicates: {len(unique_listings)}")
        
        return unique_listings

def main():
    print("Manual Comprehensive OLX Scraper")
    print("="*50)
    print("Get ALL listings without browser automation!")
    
    scraper = ManualComprehensiveScraper()
    
    choice = input("\nChoose option:\n1. Show detailed instructions\n2. Process existing HTML file\nEnter choice (1 or 2): ").strip()
    
    if choice == "1":
        scraper.get_detailed_instructions()
        
        input("\nPress Enter after you've saved the complete HTML file...")
        
        html_file = input("Enter HTML filename (default: olx_complete.html): ").strip()
        html_file = html_file or "olx_complete.html"
        
    elif choice == "2":
        html_file = input("Enter HTML filename: ").strip()
        if not html_file:
            print("Please provide a filename!")
            return
    else:
        print("Invalid choice!")
        return
    
    # Process the file
    listings = scraper.process_html_file(html_file)
    
    if listings:
        # Save results
        json_file, csv_file = scraper.save_comprehensive_results(listings)
        
        # Print summary
        scraper.print_comprehensive_summary(listings)
        
        print(f"\n🎉 SUCCESS! Extracted {len(listings)} listings!")
        
    else:
        print("\n❌ No listings extracted.")
        print("\nTroubleshooting:")
        print("1. Make sure you scrolled extensively before saving")
        print("2. Save as 'Webpage, Complete' not just HTML")
        print("3. Try a different browser to save the page")

if __name__ == "__main__":
    main()'''