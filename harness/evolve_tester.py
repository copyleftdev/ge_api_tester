"""
Main evolution harness for the genetic algorithm API tester

This script coordinates the genetic algorithm process to evolve API test payloads
that discover interesting behaviors in the target API.
"""
import random
import json
import time
import logging
import os
import argparse
from datetime import datetime
from typing import List, Dict, Any, Tuple
import statistics

# DEAP imports for genetic algorithm
from deap import base, creator, tools, algorithms

# Local imports
import grammar
import utils
from payload_tracker import payload_tracker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Genetic Algorithm Parameters ---
POPULATION_SIZE = 50
NUM_GENERATIONS = 30
CROSSOVER_PROBABILITY = 0.7
MUTATION_PROBABILITY = 0.3
TOURNAMENT_SIZE = 3

# --- Output Configuration ---
RESULTS_DIR = "./results"
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

def setup_output_directory() -> str:
    """
    Set up the output directory for storing results.
    
    Returns:
        str: Path to the output directory
    """
    # Create main results directory if it doesn't exist
    if not os.path.exists(RESULTS_DIR):
        os.makedirs(RESULTS_DIR)
    
    # Create a timestamped directory for this run
    run_dir = os.path.join(RESULTS_DIR, f"run_{TIMESTAMP}")
    os.makedirs(run_dir, exist_ok=True)
    
    # Create subdirectories for different types of outputs
    os.makedirs(os.path.join(run_dir, "stats"), exist_ok=True)
    os.makedirs(os.path.join(run_dir, "payloads"), exist_ok=True)
    
    return run_dir

def evaluate_individual(individual: Dict[str, Any]) -> Tuple[float,]:
    """
    Evaluation function for the genetic algorithm.
    Sends the payload to the API and returns the fitness score.
    
    Args:
        individual: A candidate payload to evaluate
        
    Returns:
        A tuple containing the fitness score (required by DEAP)
    """
    fitness, response_info = utils.evaluate_candidate(individual)
    return (fitness,)

def mutate_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mutation operator that modifies a payload in place.
    
    Args:
        payload: The payload to mutate
        
    Returns:
        The mutated payload
    """
    # Copy the payload to avoid modifying the original
    mutated = payload.copy()
    
    # Choose mutation strategy:
    mutation_strategy = random.choice([
        "add_field",
        "remove_field",
        "modify_field",
        "replace_field"
    ])
    
    if mutation_strategy == "add_field" or len(mutated) < 2:
        # Add a random field from another payload
        new_payload = grammar.generate_candidate()
        if new_payload:
            # Choose a random key from the new payload
            if new_payload:
                keys = list(new_payload.keys())
                if keys:
                    key = random.choice(keys)
                    mutated[key] = new_payload[key]
    
    elif mutation_strategy == "remove_field" and len(mutated) > 1:
        # Remove a random field
        key = random.choice(list(mutated.keys()))
        del mutated[key]
    
    elif mutation_strategy == "modify_field":
        # Modify an existing field
        if mutated:
            key = random.choice(list(mutated.keys()))
            
            # Handle different field types appropriately
            if isinstance(mutated[key], str):
                # For strings, either completely replace or slightly modify
                if random.random() < 0.5:
                    mutated[key] = grammar.generate_random_chars()
                else:
                    # Add some characters to the existing string
                    mutated[key] += grammar.generate_random_chars(1, 5)
            
            elif isinstance(mutated[key], int):
                # For integers, either replace or adjust value
                if random.random() < 0.5:
                    # Replace with a completely new value
                    mutated[key] = grammar.generate_random_age()
                else:
                    # Adjust the existing value
                    adjustment = random.randint(-10, 10)
                    mutated[key] = mutated[key] + adjustment
            
            elif isinstance(mutated[key], list):
                # For lists, add, remove or replace items
                if not mutated[key] or random.random() < 0.3:
                    # Replace with new hobbies if list is empty or 30% chance
                    mutated[key] = grammar.generate_random_hobbies()
                elif random.random() < 0.5:
                    # Add a new item
                    if isinstance(mutated[key][0], str):  # Assume it's a list of strings
                        mutated[key].append(grammar.generate_random_chars())
                else:
                    # Remove a random item if there's more than one
                    if len(mutated[key]) > 1:
                        mutated[key].pop(random.randrange(len(mutated[key])))
            
            elif isinstance(mutated[key], bool):
                # For booleans, flip the value
                mutated[key] = not mutated[key]
            
            elif isinstance(mutated[key], float):
                # For floats, adjust by a small random amount
                adjustment = random.uniform(-0.5, 0.5)
                mutated[key] = mutated[key] + adjustment
    
    else:  # replace_field
        # Replace an existing field with a completely new value
        if mutated:
            key = random.choice(list(mutated.keys()))
            
            # Generate a new value based on the field name
            if key == "name":
                mutated[key] = grammar.generate_random_chars()
            elif key == "age":
                mutated[key] = grammar.generate_random_age()
            elif key == "email":
                mutated[key] = grammar.generate_random_email()
            elif key == "zipcode":
                mutated[key] = grammar.generate_random_zipcode()
            elif key == "hobbies":
                mutated[key] = grammar.generate_random_hobbies()
            elif key == "username" or key == "password":
                mutated[key] = grammar.generate_random_chars(4, 12)
            else:
                # For unknown fields, generate a generic value
                if isinstance(mutated[key], int):
                    mutated[key] = random.randint(0, 1000)
                elif isinstance(mutated[key], str):
                    mutated[key] = grammar.generate_random_chars()
                elif isinstance(mutated[key], bool):
                    mutated[key] = random.choice([True, False])
                elif isinstance(mutated[key], float):
                    mutated[key] = random.uniform(0, 10)
                elif isinstance(mutated[key], list):
                    # Replace with a list of random strings
                    mutated[key] = [grammar.generate_random_chars() for _ in range(random.randint(1, 5))]
    
    # Important: Return a DEAP Individual object, not a regular dict
    result = creator.Individual(mutated)
    return result

def crossover_payloads(parent1: Dict[str, Any], parent2: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Crossover operator that creates two children from two parent payloads.
    
    Args:
        parent1: First parent payload
        parent2: Second parent payload
        
    Returns:
        Tuple containing two child payloads
    """
    # Create empty children with separate memory
    child1 = {}
    child2 = {}
    
    # Get all unique keys from both parents
    all_keys = set(list(parent1.keys()) + list(parent2.keys()))
    
    # For each key, decide which child gets which parent's value
    for key in all_keys:
        # If both parents have the key, randomly assign to children
        if key in parent1 and key in parent2:
            if random.random() < 0.5:
                child1[key] = parent1[key]
                child2[key] = parent2[key]
            else:
                child1[key] = parent2[key]
                child2[key] = parent1[key]
        
        # If only parent1 has the key, decide whether to pass it on
        elif key in parent1:
            if random.random() < 0.7:  # 70% chance to inherit
                # Randomly decide which child gets the value
                if random.random() < 0.5:
                    child1[key] = parent1[key]
                else:
                    child2[key] = parent1[key]
        
        # If only parent2 has the key, decide whether to pass it on
        elif key in parent2:
            if random.random() < 0.7:  # 70% chance to inherit
                # Randomly decide which child gets the value
                if random.random() < 0.5:
                    child1[key] = parent2[key]
                else:
                    child2[key] = parent2[key]
    
    # Ensure each child has at least one field
    if not child1:
        # If child1 is empty, give it a random field from parent1
        key = random.choice(list(parent1.keys()))
        child1[key] = parent1[key]
    
    if not child2:
        # If child2 is empty, give it a random field from parent2
        key = random.choice(list(parent2.keys()))
        child2[key] = parent2[key]
    
    # Important: Return DEAP Individual objects, not regular dicts
    result1 = creator.Individual(child1)
    result2 = creator.Individual(child2)
    return result1, result2

def save_generation_stats(stats: Dict[str, List[float]], generation: int, directory: str) -> None:
    """
    Save statistics about a generation to a file.
    
    Args:
        stats: Dictionary of statistics
        generation: Generation number
        directory: Directory to save the file in
    """
    filename = os.path.join(directory, f"generation_{generation:03d}_stats.json")
    
    # Calculate additional statistics
    output_stats = {}
    for key, values in stats.items():
        if values:
            output_stats[key] = {
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
                "median": statistics.median(values),
                "std": statistics.stdev(values) if len(values) > 1 else 0
            }
    
    # Save to file
    with open(filename, 'w') as f:
        json.dump(output_stats, f, indent=2)

def save_best_payloads(population: List[Dict[str, Any]], fitnesses: List[float], 
                      directory: str, top_n: int = 10) -> None:
    """
    Save the best payloads from the current population.
    
    Args:
        population: List of payloads
        fitnesses: List of corresponding fitness values
        directory: Directory to save the file in
        top_n: Number of top payloads to save
    """
    # Pair payloads with their fitness values
    payload_fitness_pairs = list(zip(population, fitnesses))
    
    # Sort by fitness in descending order
    payload_fitness_pairs.sort(key=lambda x: x[1], reverse=True)
    
    # Select top N payloads
    top_payloads = payload_fitness_pairs[:top_n]
    
    # Save to file
    filename = os.path.join(directory, f"top_{top_n}_payloads.json")
    with open(filename, 'w') as f:
        json.dump([
            {"payload": p, "fitness": float(f)} 
            for p, f in top_payloads
        ], f, indent=2)

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Genetic Evolution API Tester')
    
    parser.add_argument('--population', type=int, default=POPULATION_SIZE,
                        help=f'Population size (default: {POPULATION_SIZE})')
    
    parser.add_argument('--generations', type=int, default=NUM_GENERATIONS,
                        help=f'Number of generations (default: {NUM_GENERATIONS})')
    
    parser.add_argument('--crossover', type=float, default=CROSSOVER_PROBABILITY,
                        help=f'Crossover probability (default: {CROSSOVER_PROBABILITY})')
    
    parser.add_argument('--mutation', type=float, default=MUTATION_PROBABILITY,
                        help=f'Mutation probability (default: {MUTATION_PROBABILITY})')
    
    parser.add_argument('--tournament', type=int, default=TOURNAMENT_SIZE,
                        help=f'Tournament size for selection (default: {TOURNAMENT_SIZE})')
    
    return parser.parse_args()

def main():
    """Main function to run the genetic algorithm."""
    # Parse command line arguments
    args = parse_arguments()
    
    # Set up output directory
    output_dir = setup_output_directory()
    logger.info(f"Results will be stored in: {output_dir}")
    
    # Set up the genetic algorithm
    creator.create("FitnessMax", base.Fitness, weights=(1.0,))
    creator.create("Individual", dict, fitness=creator.FitnessMax)
    
    toolbox = base.Toolbox()
    
    # Register generation functions
    toolbox.register("individual", lambda: creator.Individual(grammar.generate_candidate()))
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)
    
    # Register genetic operators
    toolbox.register("evaluate", evaluate_individual)
    toolbox.register("mate", crossover_payloads)
    toolbox.register("mutate", mutate_payload)
    toolbox.register("select", tools.selTournament, tournsize=args.tournament)
    
    # Create initial population
    logger.info(f"Creating initial population of {args.population} individuals")
    pop = toolbox.population(n=args.population)
    
    # Evaluate initial population
    logger.info("Evaluating initial population")
    fitnesses = list(map(toolbox.evaluate, pop))
    for ind, fit in zip(pop, fitnesses):
        ind.fitness.values = fit
    
    # Statistics to track
    stats = tools.Statistics(lambda ind: ind.fitness.values[0])
    stats.register("avg", statistics.mean)
    stats.register("min", min)
    stats.register("max", max)
    
    # Run the genetic algorithm
    logger.info(f"Starting evolution for {args.generations} generations")
    start_time = time.time()
    
    # Initialize tracking variables
    all_gen_stats = {}
    best_individual = None
    best_fitness = 0
    
    # Loop through generations
    for gen in range(args.generations):
        gen_start_time = time.time()
        
        # Generate offspring using our custom implementation instead of varAnd
        # Select the parents
        offspring = toolbox.select(pop, len(pop))
        # Apply crossover and mutation on the offspring
        offspring = list(map(toolbox.clone, offspring))
        
        # Apply crossover in pairs
        for i in range(1, len(offspring), 2):
            if random.random() < args.crossover:
                offspring[i-1], offspring[i] = toolbox.mate(offspring[i-1], offspring[i])
                del offspring[i-1].fitness.values
                del offspring[i].fitness.values
        
        # Apply mutation
        for i in range(len(offspring)):
            if random.random() < args.mutation:
                offspring[i] = toolbox.mutate(offspring[i])
                del offspring[i].fitness.values
        
        # Evaluate offspring
        invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
        fitnesses = map(toolbox.evaluate, invalid_ind)
        for ind, fit in zip(invalid_ind, fitnesses):
            ind.fitness.values = fit
        
        # Select the next generation
        pop = toolbox.select(offspring, k=len(pop))
        
        # Collect statistics for this generation
        gen_stats = stats.compile(pop)
        logger.info(f"Generation {gen+1}: {gen_stats}")
        
        # Save generation statistics
        for key, value in gen_stats.items():
            if key not in all_gen_stats:
                all_gen_stats[key] = []
            all_gen_stats[key].append(value)
        
        # Save statistics to file
        save_generation_stats(
            {key: [values[gen]] for key, values in all_gen_stats.items()},
            gen+1, 
            os.path.join(output_dir, "stats")
        )
        
        # Find the best individual in this generation
        gen_best = tools.selBest(pop, 1)[0]
        gen_best_fitness = gen_best.fitness.values[0]
        
        # Update the overall best if this generation's best is better
        if gen_best_fitness > best_fitness:
            best_individual = gen_best
            best_fitness = gen_best_fitness
            
            logger.info(f"New best individual with fitness {best_fitness}: {json.dumps(best_individual)}")
        
        # Save the best payloads from this generation
        current_fitnesses = [ind.fitness.values[0] for ind in pop]
        save_best_payloads(
            pop, current_fitnesses,
            os.path.join(output_dir, "payloads"),
            top_n=10
        )
        
        # Calculate and log generation time
        gen_time = time.time() - gen_start_time
        logger.info(f"Generation {gen+1} completed in {gen_time:.2f} seconds")
    
    # Save tracked payloads
    logger.info("Saving tracked payloads")
    payload_tracker.save_to_disk()
    
    # Print payload tracker statistics
    payload_tracker.print_summary()
    
    # Log total runtime
    total_time = time.time() - start_time
    logger.info(f"Evolution completed in {total_time:.2f} seconds")
    
    # Return the final population and the best individual
    return pop, best_individual

if __name__ == "__main__":
    main()
