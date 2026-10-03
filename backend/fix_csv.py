#!/usr/bin/env python3
"""
Fix the click_logs.csv file to ensure proper formatting and headers
This will resolve the analytics parsing issues
"""

import csv
import os
import pandas as pd
from datetime import datetime
from pathlib import Path

def fix_csv_file():
    """Fix the CSV file format and add proper headers"""
    
    # Path to the CSV file
    csv_file = Path("data/click_logs.csv")
    backup_file = Path("data/click_logs_backup.csv")
    
    print("🔧 Fixing CSV file format...")
    
    if not csv_file.exists():
        print(f"❌ CSV file not found: {csv_file}")
        return False
    
    # Create backup
    try:
        import shutil
        shutil.copy2(csv_file, backup_file)
        print(f"✅ Backup created: {backup_file}")
    except Exception as e:
        print(f"⚠️ Could not create backup: {e}")
    
    # Read the current content
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        print(f"📄 Current file content preview:")
        print(f"   First 200 chars: {content[:200]}...")
        
        # Split into lines
        lines = content.split('\n')
        print(f"📊 Found {len(lines)} lines")
        
        # Check if first line looks like headers
        first_line = lines[0] if lines else ""
        has_headers = 'timestamp' in first_line and 'user_email' in first_line
        
        if has_headers:
            print("✅ Headers detected")
            data_lines = lines[1:]  # Skip header line
        else:
            print("❌ No headers detected - will add them")
            data_lines = lines
        
        # Parse data lines
        parsed_data = []
        for i, line in enumerate(data_lines):
            if not line.strip():
                continue
                
            # Split by whitespace, but be careful with user agents
            parts = line.split()
            
            if len(parts) >= 6:
                # Reconstruct user agent (everything between IP and referer)
                timestamp = parts[0]
                user_email = parts[1]
                action_id = parts[2]
                ip_address = parts[3]
                
                # User agent is everything from part 4 until the last part (referer)
                user_agent = ' '.join(parts[4:-1])
                referer = parts[-1]
                
                # Fix common issues
                if not user_email.endswith('.com') and not user_email.endswith('.org'):
                    user_email = user_email + 'm'  # Fix truncated .com
                
                parsed_data.append({
                    'timestamp': timestamp,
                    'user_email': user_email,
                    'action_id': action_id,
                    'ip_address': ip_address,
                    'user_agent': user_agent,
                    'referer': referer
                })
                
                print(f"   ✅ Parsed line {i+1}: {user_email} -> {action_id}")
            else:
                print(f"   ⚠️ Skipped malformed line {i+1}: {line[:50]}...")
        
        print(f"📊 Successfully parsed {len(parsed_data)} records")
        
        # Write the fixed CSV file
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            if parsed_data:
                fieldnames = ['timestamp', 'user_email', 'action_id', 'ip_address', 'user_agent', 'referer']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                
                # Write headers
                writer.writeheader()
                
                # Write data
                for row in parsed_data:
                    writer.writerow(row)
                
                print(f"✅ Fixed CSV file written with {len(parsed_data)} records")
                return True
            else:
                print(f"❌ No valid data found to write")
                return False
                
    except Exception as e:
        print(f"❌ Error fixing CSV file: {e}")
        return False

def verify_fixed_csv():
    """Verify the fixed CSV file can be read properly"""
    
    csv_file = Path("data/click_logs.csv")
    
    print(f"\n🔍 Verifying fixed CSV file...")
    
    try:
        # Try reading with pandas (same as analytics engine)
        df = pd.read_csv(csv_file)
        
        print(f"✅ Pandas can read the file:")
        print(f"   📊 Shape: {df.shape}")
        print(f"   📋 Columns: {list(df.columns)}")
        print(f"   👥 Unique users: {df['user_email'].nunique()}")
        print(f"   🎯 Unique actions: {df['action_id'].nunique()}")
        
        # Show sample data
        print(f"\n📋 Sample data:")
        print(df.head().to_string())
        
        # Test timestamp parsing
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        print(f"✅ Timestamps parse correctly")
        print(f"   📅 Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        
        return True
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False

def test_analytics_after_fix():
    """Test the analytics endpoints after fixing the CSV"""
    
    print(f"\n🧪 Testing analytics endpoints...")
    
    import requests
    
    API_BASE = "http://localhost:8080"
    
    try:
        # Test analytics health
        response = requests.get(f"{API_BASE}/analytics/health", timeout=10)
        if response.ok:
            health = response.json()
            print(f"✅ Analytics Health:")
            print(f"   📊 Pandas Data Points: {health['pandas_data_points']}")
            print(f"   ⚡ Polars Data Points: {health['polars_data_points']}")
            print(f"   🎯 Status: {health['status']}")
            
            if health['pandas_data_points'] > 0:
                print(f"🎉 SUCCESS: Analytics now detects data!")
            else:
                print(f"⚠️ Still showing 0 data points - may need server restart")
        else:
            print(f"❌ Analytics health check failed: {response.status_code}")
            
        # Test basic analysis
        response = requests.post(f"{API_BASE}/analytics/analyze", 
                               json={"engine": "pandas", "time_range": "7d"},
                               timeout=10)
        if response.ok:
            data = response.json()
            summary = data.get('summary', {})
            print(f"✅ Basic Analysis:")
            print(f"   📊 Total Records: {summary.get('total_records', 'N/A')}")
            print(f"   👥 Unique Users: {summary.get('unique_users', 'N/A')}")
            print(f"   ⚠️ Avg Risk Score: {summary.get('avg_risk_score', 'N/A')}")
        else:
            print(f"❌ Basic analysis failed: {response.status_code}")
            
    except requests.RequestException as e:
        print(f"⚠️ Cannot test analytics - server may not be running: {e}")

def main():
    """Main execution function"""
    
    print("🎣 CSV File Fixer for Phishing Analytics")
    print("=" * 50)
    
    # Check if data directory exists
    data_dir = Path("data")
    if not data_dir.exists():
        print(f"❌ Data directory not found: {data_dir}")
        print(f"   Are you running this from the project root directory?")
        return
    
    # Fix the CSV file
    if fix_csv_file():
        # Verify the fix worked
        if verify_fixed_csv():
            # Test analytics
            test_analytics_after_fix()
            
            print(f"\n🎉 CSV FILE FIXED SUCCESSFULLY!")
            print(f"Your analytics should now work properly.")
            print(f"\n📋 Next Steps:")
            print(f"   1. Refresh your analytics dashboard")
            print(f"   2. Check if metrics now show real data")
            print(f"   3. If still showing 0, restart your backend server")
            print(f"   4. The backup is saved as: data/click_logs_backup.csv")
        else:
            print(f"\n❌ Fix verification failed")
    else:
        print(f"\n❌ CSV file fix failed")

if __name__ == "__main__":
    main()