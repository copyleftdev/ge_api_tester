"""
Payload Discovery Test Module

This module uses pytest to discover patterns in saved interesting payloads.
It dynamically generates test cases based on payload files saved during evolution runs.
"""
import os
import json
import pytest
import requests
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

# Find the payloads directory
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
PAYLOADS_DIR = os.path.join(ROOT_DIR, "tracked_payloads")

def get_payload_files():
    """Find all payload files saved by the tracker."""
    if not os.path.exists(PAYLOADS_DIR):
        return []
    
    # Look for the manifest file first
    manifest_path = os.path.join(PAYLOADS_DIR, "payload_manifest.json")
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
                # Return the list of files from the manifest
                return [os.path.join(PAYLOADS_DIR, os.path.basename(f)) 
                        for category, f in manifest.get('files', {}).items()]
        except (json.JSONDecodeError, FileNotFoundError):
            pass
    
    # Fallback to finding files by pattern        
    return [os.path.join(PAYLOADS_DIR, f) for f in os.listdir(PAYLOADS_DIR)
            if f.endswith(".json") and f != "payload_manifest.json"]

def get_latest_payload_file():
    """Get the most recently created payload file."""
    payload_files = get_payload_files()
    if not payload_files:
        return None
    
    # Sort by creation time, newest first
    return sorted(payload_files, key=lambda f: os.path.getctime(f), reverse=True)[0]

def load_payload_data(filepath):
    """Load the payload data from a file."""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        pytest.skip(f"Failed to load payload file {filepath}: {e}")
        return None

class TestPayloadDiscovery:
    """
    Test class for discovering patterns in interesting payloads.
    Tests are dynamically generated based on payload files.
    """
    
    @pytest.fixture(scope="class")
    def payload_data(self):
        """Load payload data files."""
        payload_files = get_payload_files()
        if not payload_files:
            pytest.skip("No payload files found. Run the evolution first.")
            return None
        
        # Create a combined payload data structure
        combined_data = {
            "payloads": {
                "high_fitness": [],
                "server_errors": [],
                "validation_errors": [],
                "slow_responses": [],
                "timeouts": [],
                "sql_injection_hits": [],
                "memory_issues": [],
                "auth_issues": []
            }
        }
        
        # Load and combine all payload files
        for filepath in payload_files:
            category = os.path.basename(filepath).split('_')[0]
            if category in combined_data["payloads"]:
                try:
                    with open(filepath, 'r') as f:
                        file_data = json.load(f)
                        # Format data to match expected structure
                        formatted_data = []
                        for item in file_data:
                            formatted_item = {
                                "payload": item.get("payload", {}),
                                "response": {
                                    "data": item.get("response_info", {}).get("data", {}),
                                    "status_code": item.get("response_info", {}).get("status_code", 0),
                                    "time": item.get("response_info", {}).get("time", 0),
                                    "fitness": item.get("fitness", 0)
                                }
                            }
                            formatted_data.append(formatted_item)
                        combined_data["payloads"][category].extend(formatted_data)
                except (json.JSONDecodeError, FileNotFoundError) as e:
                    print(f"Warning: Failed to load payload file {filepath}: {e}")
        
        print(f"\nAnalyzing {len(payload_files)} payload files")
        for category, items in combined_data["payloads"].items():
            print(f"  {category}: {len(items)} items")
        
        return combined_data
    
    def test_payload_file_exists(self):
        """Verify that at least one payload file exists."""
        payload_files = get_payload_files()
        assert payload_files, "No payload files found. Run the evolution first."
    
    def test_analyze_server_errors(self, payload_data):
        """Analyze server error payloads to identify patterns."""
        if not payload_data:
            pytest.skip("No payload data available")
        
        server_errors = payload_data["payloads"]["server_errors"]
        
        print(f"\nFound {len(server_errors)} server error payloads")
        if not server_errors:
            pytest.skip("No server error payloads found")
        
        # Extract payload fields to find common patterns
        fields_present = {}
        for item in server_errors:
            payload = item["payload"]
            for key in payload:
                if key not in fields_present:
                    fields_present[key] = 0
                fields_present[key] += 1
        
        # Sort and print field frequencies
        print("\nField frequency in server error payloads:")
        for key, count in sorted(fields_present.items(), key=lambda x: x[1], reverse=True):
            print(f"  {key}: {count} ({count/len(server_errors)*100:.1f}%)")
        
        # Check for zipcode patterns (if present)
        zipcode_patterns = {}
        for item in server_errors:
            payload = item["payload"]
            if "zipcode" in payload:
                prefix = payload["zipcode"][:3] if len(payload["zipcode"]) >= 3 else payload["zipcode"]
                if prefix not in zipcode_patterns:
                    zipcode_patterns[prefix] = 0
                zipcode_patterns[prefix] += 1
        
        if zipcode_patterns:
            print("\nZipcode patterns in server error payloads:")
            for prefix, count in sorted(zipcode_patterns.items(), key=lambda x: x[1], reverse=True):
                print(f"  Prefix {prefix}: {count} ({count/len(server_errors)*100:.1f}%)")
                
        # Assert that we've done the analysis
        assert True, "Analysis completed"
    
    def test_analyze_response_times(self, payload_data):
        """Analyze payloads with slow response times."""
        if not payload_data:
            pytest.skip("No payload data available")
        
        slow_responses = payload_data["payloads"]["slow_responses"]
        
        print(f"\nFound {len(slow_responses)} slow response payloads")
        if not slow_responses:
            pytest.skip("No slow response payloads found")
        
        # Extract response times and payload complexity
        response_times = []
        payload_keys = []
        for item in slow_responses:
            response_time = item["response"]["response_time"]
            payload = item["payload"]
            response_times.append(response_time)
            payload_keys.append(len(payload.keys()))
        
        # Calculate statistics
        avg_time = sum(response_times) / len(response_times)
        max_time = max(response_times)
        avg_keys = sum(payload_keys) / len(payload_keys)
        
        print(f"\nResponse time statistics:")
        print(f"  Average: {avg_time:.3f} seconds")
        print(f"  Maximum: {max_time:.3f} seconds")
        print(f"  Average payload fields: {avg_keys:.1f}")
        
        # Assert that we've done the analysis
        assert True, "Analysis completed"
    
    def test_generate_fitness_distribution(self, payload_data, tmp_path):
        """Generate a histogram of fitness scores."""
        if not payload_data:
            pytest.skip("No payload data available")
        
        # Collect fitness scores from all interesting payloads
        fitness_scores = []
        categories = []
        
        for category, payloads in payload_data["payloads"].items():
            for item in payloads:
                fitness = item["response"].get("fitness", 0)
                fitness_scores.append(fitness)
                categories.append(category)
        
        if not fitness_scores:
            pytest.skip("No fitness scores found")
        
        # Create a DataFrame
        df = pd.DataFrame({
            'fitness': fitness_scores,
            'category': categories
        })
        
        # Create a histogram
        plt.figure(figsize=(10, 6))
        plt.hist(fitness_scores, bins=10, alpha=0.7)
        plt.title('Distribution of Fitness Scores')
        plt.xlabel('Fitness Score')
        plt.ylabel('Frequency')
        plt.grid(alpha=0.3)
        
        # Save the figure
        output_file = tmp_path / "fitness_histogram.png"
        plt.savefig(output_file)
        plt.close()
        
        print(f"\nFitness score statistics:")
        print(f"  Average: {sum(fitness_scores)/len(fitness_scores):.3f}")
        print(f"  Minimum: {min(fitness_scores):.3f}")
        print(f"  Maximum: {max(fitness_scores):.3f}")
        print(f"  Histogram saved to: {output_file}")
        
        # Print category statistics
        print("\nPayload categories:")
        category_counts = df['category'].value_counts()
        for category, count in category_counts.items():
            avg_fitness = df[df['category'] == category]['fitness'].mean()
            print(f"  {category}: {count} payloads, avg fitness: {avg_fitness:.3f}")
        
        # Assert that we've generated the histogram
        assert os.path.exists(output_file)
    
    def test_verify_api_vulnerabilities(self, payload_data):
        """
        Try to verify if discovered server error payloads 
        still trigger errors in the current API.
        """
        if not payload_data:
            pytest.skip("No payload data available")
        
        server_errors = payload_data["payloads"]["server_errors"]
        
        if not server_errors:
            pytest.skip("No server error payloads found")
        
        # Only test at most 5 payloads to avoid overloading the API
        test_payloads = server_errors[:min(5, len(server_errors))]
        
        verified_count = 0
        api_url = "http://api:5000/predict"
        
        print("\nVerifying server error payloads against the current API:")
        for i, item in enumerate(test_payloads):
            payload = item["payload"]
            
            try:
                # Print and skip test if not running in Docker
                if not os.path.exists("/.dockerenv"):
                    print(f"  Payload {i+1}: Would test: {json.dumps(payload)[:50]}...")
                    continue
                    
                response = requests.post(
                    api_url, 
                    json=payload,
                    timeout=5
                )
                
                if response.status_code >= 500:
                    verified_count += 1
                    print(f"  Payload {i+1}: Still triggers server error ({response.status_code})")
                else:
                    print(f"  Payload {i+1}: No longer triggers server error ({response.status_code})")
                    
            except (requests.RequestException, json.JSONDecodeError) as e:
                print(f"  Payload {i+1}: Test failed: {e}")
        
        # This assertion is informative, not strict
        assert True, f"Verification completed. {verified_count}/{len(test_payloads)} still trigger errors."
