#!/usr/bin/env python
"""
Run Payload Discovery - Executes the genetic evolution and then runs pytest discovery

This script first runs the genetic evolution process to find interesting payloads,
then automatically runs the pytest discovery module to analyze those payloads.
"""
import os
import sys
import time
import subprocess
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_evolution():
    """Run the genetic evolution process"""
    logger.info("Starting genetic evolution process...")
    
    # Import and run the main evolution function
    from evolve_tester import main
    main()
    
    logger.info("Evolution process completed.")

def run_payload_discovery():
    """Run the pytest discovery process on the saved payloads"""
    logger.info("Starting payload discovery with pytest...")
    
    # Ensure the pyc files are regenerated if source changed
    os.environ["PYTHONDONTWRITEBYTECODE"] = "0"
    
    # Path to the discovery test
    test_path = os.path.join(os.path.dirname(__file__), "tests", "test_payload_discovery.py")
    
    # Run pytest with verbose output
    cmd = ["pytest", test_path, "-v", "--no-header"]
    
    if not os.path.exists("/.dockerenv"):
        logger.warning("Not running in Docker container - API connectivity tests will be skipped")
    
    try:
        # Run pytest as a subprocess
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Stream output in real-time
        for line in process.stdout:
            print(line, end='')
        
        # Wait for process to complete
        process.wait()
        
        if process.returncode != 0:
            logger.error(f"Pytest discovery failed with return code {process.returncode}")
        else:
            logger.info("Payload discovery completed successfully")
            
    except Exception as e:
        logger.error(f"Error running payload discovery: {e}")

if __name__ == "__main__":
    try:
        # Check if we should skip the evolution step
        skip_evolution = "--skip-evolution" in sys.argv
        
        if not skip_evolution:
            run_evolution()
            # Small delay to ensure files are written
            time.sleep(1)
        else:
            logger.info("Skipping evolution step")
        
        # Run the discovery process
        run_payload_discovery()
        
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        sys.exit(1)
