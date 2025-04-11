#!/usr/bin/env python3
"""
Run Payload Discovery - Executes the genetic evolution and then runs pytest discovery

This script first runs the genetic evolution process to find interesting payloads,
then automatically runs the pytest discovery module to analyze those payloads.
"""
import os
import sys
import logging
import argparse
import json
import subprocess
from datetime import datetime
import multiprocessing

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set number of worker processes for parallel testing
# Use fewer processes in Docker to avoid resource contention
DOCKER_MODE = os.path.exists("/.dockerenv")
NUM_PROCESSES = 2 if DOCKER_MODE else 4

def run_evolution(args=None):
    """Run the genetic evolution process."""
    logger.info("Starting genetic evolution process...")
    
    # Build command
    cmd = ["python", "harness/evolve_tester.py"]
    if args:
        if args.population:
            cmd.extend(["--population", str(args.population)])
        if args.generations:
            cmd.extend(["--generations", str(args.generations)])
        if args.crossover:
            cmd.extend(["--crossover", str(args.crossover)])
        if args.mutation:
            cmd.extend(["--mutation", str(args.mutation)])
    
    # Execute evolution process
    try:
        subprocess.run(cmd, check=True)
        logger.info("Evolution process completed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Evolution process failed with exit code {e.returncode}")
        return False

def analyze_results():
    """Analyze the results of the genetic evolution process."""
    logger.info("Analyzing test results...")
    
    # Run pytest to analyze the results
    try:
        subprocess.run(["pytest", "harness/tests/test_payload_discovery.py", "-v"], check=True)
        logger.info("Test analysis completed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Test analysis failed with exit code {e.returncode}")
        return False

def run_parallel_tests(num_runs=3):
    """Run multiple tests in parallel."""
    logger.info(f"Running {num_runs} tests in parallel with {NUM_PROCESSES} processes")
    
    with multiprocessing.Pool(processes=NUM_PROCESSES) as pool:
        results = pool.map(lambda _: run_evolution(), range(num_runs))
    
    success_count = sum(1 for result in results if result)
    logger.info(f"Completed {success_count}/{num_runs} tests successfully")
    
    # Analyze all results
    analyze_results()

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Run the genetic evolution API tester.')
    parser.add_argument('--parallel', action='store_true', help='Run tests in parallel')
    parser.add_argument('--runs', type=int, default=3, help='Number of parallel runs')
    parser.add_argument('--population', type=int, help='Population size')
    parser.add_argument('--generations', type=int, help='Number of generations')
    parser.add_argument('--crossover', type=float, help='Crossover probability')
    parser.add_argument('--mutation', type=float, help='Mutation probability')
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    
    if args.parallel:
        run_parallel_tests(args.runs)
    else:
        run_evolution(args)
        analyze_results()
