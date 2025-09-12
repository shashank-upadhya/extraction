# from bs4 import BeautifulSoup
# import json
# import csv
# import re
# from datetime import datetime
# import os

# class EnhancedOLXParser:
#     def __init__(self, html_file_path):
#         self.html_file_path = html_file_path
        
#     def analyze_html_structure(self):
#         """Analyze the HTML structure to understand the page layout"""
#         try:
#             with open(self.html_file_path, 'r', encoding='utf-8') as f:
#                 content = f.read()
            
#             soup = BeautifulSoup(content, 'html.parser')
            
#             print("="*60)
#             print("HTML STRUCTURE ANALYSIS")
#             print("="*60)
            
#             # Basic page info
#             title = soup.find('title')
#             print(f"Page Title: {title.text if title else 'Not found'}")
            
#             # Check for common OLX indicators
#             olx_indicators = [
#                 'olx', 'item', 'listing', 'product', 'ad', 'classified'
#             ]
            
#             found_indicators = []
#             for indicator in olx_indicators:
#                 elements = soup.find_all(class_=lambda x: x and indicator in x.lower())
#                 if elements:
#                     found_indicators.append(f"{indicator}: {len(elements)} elements")
            
#             print(f"OLX-related elements found: {', '.join(found_indicators) if found_indicators else 'None'}")
            
#             # Find all elements with data attributes (common in modern websites)
#             data_elements = soup.find_all(attrs={'data-aut-id': True})
#             print(f"Elements with data-aut-id: {len(data_elements)}")
            
#             if data_elements:
#                 unique_data_ids = set([elem.get('data-aut-id') for elem in data_elements])
#                 print("Common data-aut-id values:")
#                 for data_id in sorted(unique_data_ids)[:10]:  # Show first 10
#                     print(f"  - {data_id}")
            
#             # Look for price patterns
#             price_patterns = [r'₹\s*[\d,]+', r'Rs\.?\s*[\d,]+', r'\d+\s*rupees?']
#             prices_found = []
#             for pattern in price_patterns:
#                 matches = re.findall(pattern, content, re.IGNORECASE)
#                 prices_found.extend(matches[:5])  # Limit to 5 examples
            
#             print(f"Price patterns found: {prices_found[:10] if prices_found else 'None'}")
            
#             # Look for links that might be listings
#             all_links = soup.find_all('a', href=True)
#             item_links = [link for link in all_links if any(keyword in link.get('href', '').lower() 
#                                                            for keyword in ['item', 'ad', 'product', 'listing'])]
#             print(f"Potential listing links: {len(item_links)}")
            
#             # Check for JSON-LD or script data
#             scripts = soup.find_all('script')
#             json_scripts = [script for script in scripts if script.string and 
#                            any(keyword in script.string for keyword in ['json', 'item', 'product'])]
#             print(f"Potential JSON data scripts: {len(json_scripts)}")
            
#             # Look for common container patterns
#             container_patterns = ['container', 'wrapper', 'main', 'content', 'list', 'grid']
#             containers = []
#             for pattern in container_patterns:
#                 elements = soup.find_all(class_=lambda x: x and pattern in x.lower())
#                 if elements:
#                     containers.append(f"{pattern}: {len(elements)}")
#             print(f"Container elements: {', '.join(containers) if containers else 'None'}")
            
#             return soup
            
#         except Exception as e:
#             print(f"Error analyzing HTML structure: {e}")
#             return None
    
#     def extract_from_json_scripts(self, soup):
#         """Try to extract data from JSON scripts embedded in the page"""
#         listings = []
        
#         scripts = soup.find_all('script')
#         for script in scripts:
#             if not script.string:
#                 continue
                
#             script_content = script.string.strip()
            
#             # Look for JSON patterns that might contain listing data
#             json_patterns = [
#                 r'window\.__INITIAL_STATE__\s*=\s*({.+?});',
#                 r'window\.__APOLLO_STATE__\s*=\s*({.+?});',
#                 r'__NEXT_DATA__\s*=\s*({.+?})',
#                 r'window\.initialState\s*=\s*({.+?});'
#             ]
            
#             for pattern in json_patterns:
#                 matches = re.findall(pattern, script_content, re.DOTALL)
#                 for match in matches:
#                     try:
#                         data = json.loads(match)
#                         # Recursively search for listing-like data
#                         found_listings = self.search_json_for_listings(data)
#                         listings.extend(found_listings)
#                     except:
#                         continue
        
#         return listings
    
#     def search_json_for_listings(self, data, depth=0):
#         """Recursively search JSON data for listing information"""
#         if depth > 3:  # Prevent infinite recursion
#             return []
        
#         listings = []
        
#         if isinstance(data, dict):
#             # Look for keys that suggest listing data
#             listing_keys = ['title', 'price', 'location', 'description', 'name']
#             if any(key in data for key in listing_keys):
#                 # This might be a listing
#                 listing = {
#                     'title': data.get('title', data.get('name', 'N/A')),
#                     'price': str(data.get('price', data.get('amount', 'N/A'))),
#                     'location': data.get('location', data.get('city', 'N/A')),
#                     'date': data.get('date', data.get('createdAt', 'N/A')),
#                     'link': data.get('url', data.get('link', 'N/A')),
#                     'image_url': data.get('image', data.get('thumbnail', 'N/A')),
#                     'seller': 'N/A'
#                 }
#                 if listing['title'] != 'N/A':
#                     listings.append(listing)
            
#             # Continue searching in nested objects
#             for value in data.values():
#                 listings.extend(self.search_json_for_listings(value, depth + 1))
                
#         elif isinstance(data, list):
#             for item in data:
#                 listings.extend(self.search_json_for_listings(item, depth + 1))
        
#         return listings
    
#     def extract_with_flexible_selectors(self, soup):
#         """Try multiple selector strategies to find listings"""
#         listings = []
        
#         # Strategy 1: OLX-specific selectors
#         selectors_v1 = [
#             {'data-aut-id': 'itemBox'},
#             {'class_': lambda x: x and 'item' in x.lower()},
#             {'class_': lambda x: x and 'listing' in x.lower()},
#             {'class_': lambda x: x and 'ad' in x.lower()},
#         ]
        
#         for selector in selectors_v1:
#             elements = soup.find_all('div', selector)
#             if elements:
#                 print(f"Found {len(elements)} elements with selector: {selector}")
#                 for elem in elements:
#                     data = self.extract_from_element(elem)
#                     if data and data.get('title', 'N/A') != 'N/A':
#                         listings.append(data)
#                 break
        
#         # Strategy 2: Look for repeated patterns
#         if not listings:
#             # Find elements that repeat frequently (likely listings)
#             all_divs = soup.find_all('div')
#             class_counts = {}
            
#             for div in all_divs:
#                 classes = div.get('class', [])
#                 for cls in classes:
#                     class_counts[cls] = class_counts.get(cls, 0) + 1
            
#             # Find classes that appear multiple times (likely listing containers)
#             frequent_classes = [cls for cls, count in class_counts.items() if count >= 3]
            
#             for cls in frequent_classes[:5]:  # Try top 5 most frequent classes
#                 elements = soup.find_all('div', class_=cls)
#                 if len(elements) >= 3:  # Must have at least 3 elements
#                     print(f"Trying frequent class: {cls} ({len(elements)} elements)")
#                     temp_listings = []
#                     for elem in elements[:10]:  # Test first 10
#                         data = self.extract_from_element(elem)
#                         if data and data.get('title', 'N/A') != 'N/A':
#                             temp_listings.append(data)
                    
#                     if len(temp_listings) >= 2:  # If we found at least 2 valid listings
#                         listings.extend(temp_listings)
#                         break
        
#         # Strategy 3: Look for links with item/ad patterns
#         if not listings:
#             item_links = soup.find_all('a', href=lambda x: x and any(
#                 keyword in x.lower() for keyword in ['item', 'ad', 'product']))
            
#             print(f"Found {len(item_links)} potential item links")
#             for link in item_links[:20]:  # Process first 20 links
#                 # Get the parent container
#                 parent = link.find_parent(['div', 'li', 'article'])
#                 if parent:
#                     data = self.extract_from_element(parent)
#                     if data and data.get('title', 'N/A') != 'N/A':
#                         listings.append(data)
        
#         return listings
    
#     def extract_from_element(self, element):
#         """Extract listing data from a single element using multiple strategies"""
#         try:
#             data = {}
            
#             # Title extraction strategies
#             title_selectors = [
#                 '[data-aut-id="itemTitle"]',
#                 'h1', 'h2', 'h3', 'h4',
#                 '.title', '.name', '.heading',
#                 'a[href*="item"]'
#             ]
            
#             data['title'] = self.find_text_by_selectors(element, title_selectors)
            
#             # Price extraction
#             price_selectors = [
#                 '[data-aut-id="itemPrice"]',
#                 '.price', '.amount', '.cost',
#                 '*[class*="price"]', '*[id*="price"]'
#             ]
            
#             price_text = self.find_text_by_selectors(element, price_selectors)
#             if price_text == 'N/A':
#                 # Look for price patterns in text
#                 text = element.get_text()
#                 price_match = re.search(r'₹\s*[\d,]+|Rs\.?\s*[\d,]+', text)
#                 price_text = price_match.group() if price_match else 'N/A'
            
#             data['price'] = price_text
            
#             # Location extraction
#             location_selectors = [
#                 '[data-aut-id="item-location"]',
#                 '.location', '.place', '.city',
#                 '*[class*="location"]', '*[class*="place"]'
#             ]
            
#             data['location'] = self.find_text_by_selectors(element, location_selectors)
            
#             # Date extraction
#             date_selectors = [
#                 '[data-aut-id="item-date"]',
#                 '.date', '.time', '.posted',
#                 '*[class*="date"]', '*[class*="time"]'
#             ]
            
#             data['date'] = self.find_text_by_selectors(element, date_selectors)
            
#             # Link extraction
#             link_elem = element.find('a', href=True)
#             if link_elem:
#                 href = link_elem.get('href')
#                 if href.startswith('/'):
#                     data['link'] = f"https://www.olx.in{href}"
#                 else:
#                     data['link'] = href
#             else:
#                 data['link'] = 'N/A'
            
#             # Image extraction
#             img_elem = element.find('img')
#             data['image_url'] = img_elem.get('src', 'N/A') if img_elem else 'N/A'
            
#             data['seller'] = 'N/A'
            
#             return data
            
#         except Exception as e:
#             return None
    
#     def find_text_by_selectors(self, element, selectors):
#         """Try multiple CSS selectors to find text"""
#         for selector in selectors:
#             try:
#                 found = element.select_one(selector)
#                 if found and found.get_text(strip=True):
#                     return found.get_text(strip=True)
#             except:
#                 continue
#         return 'N/A'
    
#     def parse_html_file(self):
#         """Main parsing function with comprehensive strategies"""
#         print(f"Parsing HTML file: {self.html_file_path}")
        
#         soup = self.analyze_html_structure()
#         if not soup:
#             return []
        
#         all_listings = []
        
#         # Strategy 1: Try to extract from JSON scripts
#         print("\n1. Trying JSON script extraction...")
#         json_listings = self.extract_from_json_scripts(soup)
#         if json_listings:
#             print(f"Found {len(json_listings)} listings from JSON data")
#             all_listings.extend(json_listings)
        
#         # Strategy 2: Try flexible HTML selectors
#         print("\n2. Trying flexible HTML selectors...")
#         html_listings = self.extract_with_flexible_selectors(soup)
#         if html_listings:
#             print(f"Found {len(html_listings)} listings from HTML parsing")
#             all_listings.extend(html_listings)
        
#         # Remove duplicates based on title
#         seen_titles = set()
#         unique_listings = []
#         for listing in all_listings:
#             title = listing.get('title', '').lower()
#             if title and title != 'n/a' and title not in seen_titles:
#                 seen_titles.add(title)
#                 unique_listings.append(listing)
        
#         return unique_listings
    
#     def save_results(self, listings):
#         """Save results to files"""
#         if not listings:
#             print("No listings to save")
#             return
        
#         # Save to JSON
#         json_filename = 'olx_enhanced_parsing.json'
#         with open(json_filename, 'w', encoding='utf-8') as f:
#             json.dump({
#                 'search_query': 'car cover',
#                 'scraped_at': datetime.now().isoformat(),
#                 'total_listings': len(listings),
#                 'method': 'enhanced_html_parsing',
#                 'source_file': self.html_file_path,
#                 'listings': listings
#             }, f, indent=2, ensure_ascii=False)
        
#         # Save to CSV
#         csv_filename = 'olx_enhanced_parsing.csv'
#         fieldnames = ['title', 'price', 'location', 'date', 'link', 'image_url', 'seller']
        
#         with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
#             writer = csv.DictWriter(f, fieldnames=fieldnames)
#             writer.writeheader()
#             writer.writerows(listings)
        
#         print(f"\nResults saved:")
#         print(f"- JSON: {json_filename}")
#         print(f"- CSV: {csv_filename}")
        
#         # Print summary
#         print(f"\n{'='*50}")
#         print(f"ENHANCED PARSING SUMMARY")
#         print(f"{'='*50}")
#         print(f"Total unique listings: {len(listings)}")
#         print(f"Source file: {self.html_file_path}")
        
#         if listings:
#             print(f"\nSample listings:")
#             for i, listing in enumerate(listings[:5], 1):
#                 print(f"\n{i}. {listing['title']}")
#                 print(f"   Price: {listing['price']}")
#                 print(f"   Location: {listing['location']}")

# def main():
#     print("Enhanced OLX HTML Parser")
#     print("="*40)
#     print("This parser can handle various OLX page structures")
#     print("and includes debugging features.\n")
    
#     html_file = input("Enter HTML file path (default: olx_page.html): ").strip()
#     if not html_file:
#         html_file = "olx_page.html"
    
#     if not os.path.exists(html_file):
#         print(f"\nFile '{html_file}' not found!")
#         print("\nTo create the HTML file:")
#         print("1. Go to https://www.olx.in/items/q-car-cover")
#         print("2. Wait for the page to fully load (scroll down if needed)")
#         print("3. Right-click → 'Save as' → save as 'olx_page.html'")
#         print("4. Make sure to save as 'Webpage, Complete' if given options")
#         return
    
#     parser = EnhancedOLXParser(html_file)
#     listings = parser.parse_html_file()
    
#     if listings:
#         parser.save_results(listings)
#     else:
#         print("\nNo listings found. This could mean:")
#         print("1. The page uses heavy JavaScript (try saving after scrolling)")
#         print("2. OLX changed their HTML structure")
#         print("3. The page didn't load completely when saved")
#         print("\nTry:")
#         print("- Save the page again after fully loading")
#         print("- Scroll down to load more items before saving")
#         print("- Try a different browser to save the page")

# if __name__ == "__main__":
#     main()


import json
import csv
import re
from datetime import datetime

class CarCoverFilter:
    def __init__(self, json_file='olx_enhanced_parsing.json'):
        self.json_file = json_file
        
    def load_data(self):
        """Load the parsed data from JSON file"""
        try:
            with open(self.json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get('listings', [])
        except Exception as e:
            print(f"Error loading data: {e}")
            return []
    
    def is_car_cover_listing(self, listing):
        """Determine if a listing is actually for a car cover"""
        title = listing.get('title', '').lower()
        
        # Positive keywords for car covers
        car_cover_keywords = [
            'car cover', 'car body cover', 'vehicle cover', 'auto cover',
            'car protection', 'waterproof cover', 'dust cover', 'sun protection',
            'car tarpaulin', 'outdoor cover', 'silver cover', 'fabric cover'
        ]
        
        # Negative keywords to exclude (these are not car covers)
        exclude_keywords = [
            'parking', 'flat', 'apartment', '2bhk', '3bhk', 'house', 'plot',
            'all categories', 'other household', 'car sale', 'second hand car',
            'used car', 'buy car', 'sell car', 'car dealer', 'showroom'
        ]
        
        # Check if title contains car cover keywords
        has_car_cover_keyword = any(keyword in title for keyword in car_cover_keywords)
        
        # Check if title contains exclude keywords
        has_exclude_keyword = any(keyword in title for keyword in exclude_keywords)
        
        # Also check price range (car covers typically cost ₹200-₹5000)
        price = listing.get('price', '')
        price_numbers = re.findall(r'[\d,]+', price.replace('₹', '').replace('Rs', '').replace('.', ''))
        
        reasonable_price = True
        if price_numbers:
            try:
                price_value = int(price_numbers[0].replace(',', ''))
                # Car covers usually cost between ₹200 to ₹10,000
                reasonable_price = 200 <= price_value <= 10000
            except:
                reasonable_price = True  # If we can't parse, don't exclude
        
        return has_car_cover_keyword and not has_exclude_keyword and reasonable_price
    
    def clean_and_enhance_listing(self, listing):
        """Clean and enhance a car cover listing"""
        cleaned = listing.copy()
        
        # Clean title
        title = cleaned.get('title', '')
        # Remove extra spaces and clean up
        title = ' '.join(title.split())
        cleaned['title'] = title
        
        # Clean price
        price = cleaned.get('price', '')
        if price and price != 'N/A':
            # Extract just the numeric price
            price_match = re.search(r'₹\s*[\d,]+', price)
            if price_match:
                cleaned['price'] = price_match.group().strip()
        
        # Clean location
        location = cleaned.get('location', '')
        if location and location != 'N/A':
            # Remove extra information, keep just city/area
            location = location.split(',')[0].strip()
            cleaned['location'] = location
        
        # Add derived information
        title_lower = title.lower()
        
        # Determine cover type
        if 'waterproof' in title_lower:
            cleaned['cover_type'] = 'Waterproof'
        elif 'silver' in title_lower:
            cleaned['cover_type'] = 'Silver/Reflective'
        elif 'fabric' in title_lower or 'cloth' in title_lower:
            cleaned['cover_type'] = 'Fabric'
        elif 'plastic' in title_lower:
            cleaned['cover_type'] = 'Plastic'
        else:
            cleaned['cover_type'] = 'Standard'
        
        # Determine size if mentioned
        size_keywords = {
            'small': ['small', 'hatchback', 'swift', 'i10', 'alto'],
            'medium': ['medium', 'sedan', 'dzire', 'city', 'verna'],
            'large': ['large', 'suv', 'innova', 'scorpio', 'xuv'],
            'xl': ['xl', 'xxl', 'extra large']
        }
        
        cleaned['estimated_size'] = 'Universal'
        for size, keywords in size_keywords.items():
            if any(keyword in title_lower for keyword in keywords):
                cleaned['estimated_size'] = size.upper()
                break
        
        return cleaned
    
    def filter_and_process(self):
        """Filter and process all listings to get only car covers"""
        all_listings = self.load_data()
        print(f"Total listings loaded: {len(all_listings)}")
        
        # Filter for car covers only
        car_cover_listings = []
        for listing in all_listings:
            if self.is_car_cover_listing(listing):
                cleaned_listing = self.clean_and_enhance_listing(listing)
                car_cover_listings.append(cleaned_listing)
        
        print(f"Car cover listings found: {len(car_cover_listings)}")
        
        # Sort by price (lowest first, with N/A at the end)
        def price_sort_key(listing):
            price = listing.get('price', 'N/A')
            if price == 'N/A':
                return float('inf')
            
            price_numbers = re.findall(r'[\d,]+', price.replace('₹', '').replace('Rs', ''))
            if price_numbers:
                try:
                    return int(price_numbers[0].replace(',', ''))
                except:
                    return float('inf')
            return float('inf')
        
        car_cover_listings.sort(key=price_sort_key)
        
        return car_cover_listings
    
    def save_filtered_results(self, car_cover_listings):
        """Save the filtered car cover listings"""
        # Save to JSON
        json_filename = 'car_covers_filtered.json'
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump({
                'search_query': 'car cover',
                'filtered_at': datetime.now().isoformat(),
                'total_car_covers': len(car_cover_listings),
                'method': 'filtered_and_enhanced',
                'listings': car_cover_listings
            }, f, indent=2, ensure_ascii=False)
        
        # Save to CSV with enhanced fields
        csv_filename = 'car_covers_filtered.csv'
        if car_cover_listings:
            fieldnames = ['title', 'price', 'location', 'date', 'cover_type', 'estimated_size', 'link', 'image_url']
            
            with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for listing in car_cover_listings:
                    row = {field: listing.get(field, 'N/A') for field in fieldnames}
                    writer.writerow(row)
        
        print(f"\nFiltered results saved:")
        print(f"- JSON: {json_filename}")
        print(f"- CSV: {csv_filename}")
        
        return json_filename, csv_filename
    
    def analyze_results(self, car_cover_listings):
        """Analyze the car cover listings"""
        if not car_cover_listings:
            print("No car cover listings to analyze.")
            return
        
        print(f"\n{'='*60}")
        print(f"CAR COVER LISTINGS ANALYSIS")
        print(f"{'='*60}")
        
        # Price analysis
        prices = []
        for listing in car_cover_listings:
            price = listing.get('price', '')
            if price != 'N/A':
                price_numbers = re.findall(r'[\d,]+', price.replace('₹', '').replace('Rs', ''))
                if price_numbers:
                    try:
                        prices.append(int(price_numbers[0].replace(',', '')))
                    except:
                        pass
        
        if prices:
            print(f"Price Range: ₹{min(prices)} - ₹{max(prices)}")
            print(f"Average Price: ₹{sum(prices)//len(prices)}")
        
        # Cover type analysis
        cover_types = {}
        sizes = {}
        locations = {}
        
        for listing in car_cover_listings:
            # Count cover types
            cover_type = listing.get('cover_type', 'Unknown')
            cover_types[cover_type] = cover_types.get(cover_type, 0) + 1
            
            # Count sizes
            size = listing.get('estimated_size', 'Unknown')
            sizes[size] = sizes.get(size, 0) + 1
            
            # Count locations
            location = listing.get('location', 'Unknown')
            if location != 'N/A' and location != 'Unknown':
                locations[location] = locations.get(location, 0) + 1
        
        print(f"\nCover Types:")
        for cover_type, count in sorted(cover_types.items(), key=lambda x: x[1], reverse=True):
            print(f"  {cover_type}: {count}")
        
        print(f"\nEstimated Sizes:")
        for size, count in sorted(sizes.items(), key=lambda x: x[1], reverse=True):
            print(f"  {size}: {count}")
        
        if locations:
            print(f"\nTop Locations:")
            for location, count in sorted(locations.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"  {location}: {count}")
    
    def print_listings_summary(self, car_cover_listings):
        """Print a summary of the car cover listings"""
        print(f"\n{'='*60}")
        print(f"CAR COVER LISTINGS FOUND")
        print(f"{'='*60}")
        
        for i, listing in enumerate(car_cover_listings, 1):
            print(f"\n{i}. {listing['title']}")
            print(f"   Price: {listing.get('price', 'N/A')}")
            print(f"   Location: {listing.get('location', 'N/A')}")
            print(f"   Type: {listing.get('cover_type', 'N/A')}")
            print(f"   Size: {listing.get('estimated_size', 'N/A')}")
            if listing.get('link') != 'N/A':
                print(f"   Link: {listing['link'][:60]}...")

def main():
    print("Car Cover Listings Filter and Analyzer")
    print("="*50)
    print("This will filter your parsed OLX results to show only car covers")
    
    filter_processor = CarCoverFilter()
    
    # Filter and process listings
    car_cover_listings = filter_processor.filter_and_process()
    
    if car_cover_listings:
        # Save filtered results
        filter_processor.save_filtered_results(car_cover_listings)
        
        # Analyze results
        filter_processor.analyze_results(car_cover_listings)
        
        # Print detailed listings
        filter_processor.print_listings_summary(car_cover_listings)
        
        print(f"\n✅ Successfully filtered {len(car_cover_listings)} car cover listings!")
        print("Check the 'car_covers_filtered.json' and 'car_covers_filtered.csv' files.")
        
    else:
        print("\n❌ No car cover listings found in the parsed data.")
        print("This could mean:")
        print("1. The original search results didn't contain car covers")
        print("2. The filtering criteria is too strict")
        print("3. Try searching on OLX for 'car body cover' or 'vehicle cover' instead")

if __name__ == "__main__":
    main()