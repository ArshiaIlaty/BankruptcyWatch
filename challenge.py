#!/usr/bin/env python3
"""
BankruptcyWatch Coding Challenge Solution

This script parses address files in XML, TSV, and TXT formats,
combines them, and outputs the addresses as a JSON array sorted by ZIP code.
"""

import argparse
import json
import os
import re
import sys
import xml.etree.ElementTree as ET


def parse_xml_file(filepath):
    """Parse XML file containing address records."""
    addresses = []
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        
        for record in root.findall('record'):
            address = {}
            
            # Extract name or organization
            name = record.find('name')
            org = record.find('organization')
            if name is not None and name.text:
                address['name'] = name.text.strip()
            elif org is not None and org.text:
                address['organization'] = org.text.strip()
            else:
                continue  # Skip records without name or organization
            
            # Extract address components
            street = record.find('street')
            if street is not None and street.text:
                address['street'] = street.text.strip()
            
            city = record.find('city')
            if city is not None and city.text:
                address['city'] = city.text.strip()
            
            county = record.find('county')
            if county is not None and county.text:
                address['county'] = county.text.strip()
            
            state = record.find('state')
            if state is not None and state.text:
                address['state'] = state.text.strip()
            
            zip_code = record.find('zip')
            if zip_code is not None and zip_code.text:
                address['zip'] = zip_code.text.strip()
            
            addresses.append(address)
        
        return addresses
    except ET.ParseError as e:
        print(f"Error parsing XML file {filepath}: {e}", file=sys.stderr)
        return None


def parse_tsv_file(filepath):
    """Parse TSV file containing address records."""
    addresses = []
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            lines = file.readlines()
            
            # Extract header and validate format
            if not lines:
                print(f"Error: Empty TSV file {filepath}", file=sys.stderr)
                return None
            
            # Detect the header structure based on first line
            header = lines[0].strip().split('\t')
            
            # Process each line in the file
            for i, line in enumerate(lines[1:], 2):
                if not line.strip():
                    continue
                
                # Parse the TSV line
                fields = line.strip().split('\t')
                
                # Create an address dictionary
                address = {}
                
                # Map column data using header as guide
                column_data = {}
                for j, value in enumerate(fields):
                    if j < len(header):
                        column_data[header[j]] = value.strip()
                
                # Handle name fields (first, middle, last) or organization
                if 'organization' in column_data and column_data['organization'] and column_data['organization'] != 'N/A':
                    address['organization'] = column_data['organization']
                elif all(key in column_data for key in ['first', 'last']):
                    name_parts = [column_data['first']]
                    
                    # Add middle name if it exists and is not N/M/N
                    if 'middle' in column_data and column_data['middle'] and column_data['middle'] != 'N/M/N':
                        name_parts.append(column_data['middle'])
                    
                    name_parts.append(column_data['last'])
                    address['name'] = ' '.join(name_parts)
                
                # Handle address fields
                if 'address' in column_data and column_data['address'] and column_data['address'] != 'N/A':
                    address['street'] = column_data['address']
                
                # Handle city
                if 'city' in column_data and column_data['city'] and column_data['city'] != 'N/A':
                    address['city'] = column_data['city']
                
                # Handle county
                if 'county' in column_data and column_data['county'] and column_data['county'] != 'N/A':
                    address['county'] = column_data['county']
                
                # Handle state
                if 'state' in column_data and column_data['state'] and column_data['state'] != 'N/A':
                    address['state'] = column_data['state']
                
                # Handle ZIP code (may be split across zip and zip4 fields)
                if 'zip' in column_data and column_data['zip'] and column_data['zip'] != 'N/A':
                    zip_code = column_data['zip']
                    if 'zip4' in column_data and column_data['zip4'] and column_data['zip4'] != 'N/A':
                        zip_code = f"{zip_code}-{column_data['zip4']}"
                    address['zip'] = zip_code
                
                # Only add records that have at least name/organization and another field
                if ('name' in address or 'organization' in address) and len(address) > 1:
                    addresses.append(address)
            
            return addresses
    
    except Exception as e:
        print(f"Error parsing TSV file {filepath}: {e}", file=sys.stderr)
        return None


def parse_txt_file(filepath):
    """Parse plain text file containing address records."""
    addresses = []
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            content = file.read()
            
            # Split the content by double newlines to separate records
            records = re.split(r'\n\s*\n', content)
            
            for record in records:
                if not record.strip():
                    continue
                
                lines = [line.strip() for line in record.strip().split('\n')]
                if not lines:
                    continue
                
                address = {}
                
                # First line is either name or organization
                first_line = lines[0]
                if re.search(r'(Inc\.|LLC|Ltd\.|\bLLC\b|Company|Corp\.|Corporation)', first_line):
                    address['organization'] = first_line
                else:
                    address['name'] = first_line
                
                # Second line is typically the street address
                if len(lines) >= 2:
                    address['street'] = lines[1]
                
                # Last line typically has city, state, and zip
                if len(lines) >= 3:
                    # Try to match the last line with a pattern for city, state, zip
                    # This can handle formats like:
                    # "City, State ZIP"
                    # "City, County, State ZIP"
                    location_match = re.search(
                        r'([^,]+),\s*(?:([^,]+),\s*)?([A-Za-z]{2}|[A-Za-z]+)\s+(\d{5}(?:-\d{4})?)',
                        lines[-1]
                    )
                    
                    if location_match:
                        address['city'] = location_match.group(1).strip()
                        
                        # If county is included
                        if location_match.group(2):
                            address['county'] = location_match.group(2).strip()
                        
                        address['state'] = location_match.group(3).strip()
                        address['zip'] = location_match.group(4).strip()
                
                addresses.append(address)
            
            return addresses
    except Exception as e:
        print(f"Error parsing TXT file {filepath}: {e}", file=sys.stderr)
        return None


def normalize_zip_code(zip_code):
    """Normalize ZIP code for sorting purposes."""
    if not zip_code:
        return "00000"
    
    # Extract the base 5-digit ZIP code for sorting
    match = re.search(r'(\d{5})', zip_code)
    if match:
        return match.group(1)
    return "00000"


def parse_file(filepath):
    """Parse a file based on its extension."""
    _, ext = os.path.splitext(filepath)
    ext = ext.lower()
    
    if ext == '.xml':
        return parse_xml_file(filepath)
    elif ext == '.tsv':
        return parse_tsv_file(filepath)
    elif ext == '.txt':
        return parse_txt_file(filepath)
    else:
        print(f"Error: Unsupported file extension: {ext}", file=sys.stderr)
        return None


def main():
    """Main function to process command line arguments and handle file parsing."""
    parser = argparse.ArgumentParser(
        description='Parse address files and output JSON sorted by ZIP code.'
    )
    parser.add_argument(
        'files',
        metavar='FILE',
        nargs='+',
        help='input files to process (.xml, .tsv, or .txt)'
    )
    args = parser.parse_args()
    
    # Check if files exist
    for filepath in args.files:
        if not os.path.isfile(filepath):
            print(f"Error: File not found: {filepath}", file=sys.stderr)
            sys.exit(1)
    
    all_addresses = []
    
    # Process each file
    for filepath in args.files:
        addresses = parse_file(filepath)
        if addresses is None:
            sys.exit(1)  # Exit if there was a parsing error
        all_addresses.extend(addresses)
    
    # Sort addresses by ZIP code
    sorted_addresses = sorted(all_addresses, key=lambda x: normalize_zip_code(x.get('zip', '')))
    
    # Output as pretty-printed JSON
    print(json.dumps(sorted_addresses, indent=2))

    # Write to output.json file
    with open("output.json", "w", encoding="utf-8") as f:
        json.dump(sorted_addresses, f, indent=2)

    print(f"Successfully wrote {len(sorted_addresses)} addresses to output.json")

    sys.exit(0)


if __name__ == "__main__":
    main()
