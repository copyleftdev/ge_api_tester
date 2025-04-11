import random
import json
import time
import logging
import os
import argparse
from datetime import datetime
from typing import List, Dict, Any, Tuple
import statistics

from deap import base, creator, tools, algorithms

import grammar
import utils
from payload_tracker import payload_tracker

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

POPULATION_SIZE = 50
NUM_GENERATIONS = 30
CROSSOVER_PROBABILITY = 0.7
MUTATION_PROBABILITY = 0.3
TOURNAMENT_SIZE = 3

DOCKER_MODE = os.path.exists("/.dockerenv")
if DOCKER_MODE:
    POPULATION_SIZE = 20
    NUM_GENERATIONS = 10
    logger.info("Running in Docker container. Using optimized settings for containerized testing.")

RESULTS_DIR = "./results"
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

def setup_output_directory() -> str:
    if not os.path.exists(RESULTS_DIR):
        os.makedirs(RESULTS_DIR)
    
    run_dir = os.path.join(RESULTS_DIR, f"run_{TIMESTAMP}")
    os.makedirs(run_dir, exist_ok=True)
    
    os.makedirs(os.path.join(run_dir, "stats"), exist_ok=True)
    os.makedirs(os.path.join(run_dir, "payloads"), exist_ok=True)
    
    return run_dir

def evaluate_individual(individual: Dict[str, Any]) -> Tuple[float,]:
    fitness, response_info = utils.evaluate_candidate(individual)
    return (fitness,)

def mutate_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    mutated = payload.copy()
    
    mutation_strategy = random.choice([
        "add_field",
        "remove_field",
        "modify_field",
        "replace_field"
    ])
    
    if mutation_strategy == "add_field" or len(mutated) < 2:
        new_payload = grammar.generate_candidate()
        if new_payload:
            if new_payload:
                keys = list(new_payload.keys())
                if keys:
                    key = random.choice(keys)
                    mutated[key] = new_payload[key]
    
    elif mutation_strategy == "remove_field" and len(mutated) > 1:
        key = random.choice(list(mutated.keys()))
        del mutated[key]
    
    elif mutation_strategy == "modify_field":
        if mutated:
            key = random.choice(list(mutated.keys()))
            
            if isinstance(mutated[key], str):
                if random.random() < 0.5:
                    mutated[key] = grammar.generate_random_chars()
                else:
                    mutated[key] += grammar.generate_random_chars(1, 5)
            
            elif isinstance(mutated[key], int):
                if random.random() < 0.5:
                    mutated[key] = random.randint(0, 1000)
                else:
                    mutated[key] += random.choice([-100, -10, -1, 1, 10, 100])
            
            elif isinstance(mutated[key], float):
                if random.random() < 0.5:
                    mutated[key] = random.uniform(0, 100)
                else:
                    mutated[key] += random.choice([-10.0, -1.0, -0.1, 0.1, 1.0, 10.0])
            
            elif isinstance(mutated[key], bool):
                mutated[key] = not mutated[key]
            
            elif isinstance(mutated[key], list):
                if random.random() < 0.3 and mutated[key]:
                    mutated[key].pop(random.randrange(len(mutated[key])))
                elif random.random() < 0.6:
                    if isinstance(mutated[key], list) and all(isinstance(x, str) for x in mutated[key]):
                        mutated[key].append(grammar.generate_random_chars())
                    elif isinstance(mutated[key], list) and all(isinstance(x, int) for x in mutated[key]):
                        mutated[key].append(random.randint(0, 1000))
                    else:
                        mutated[key].append(grammar.generate_random_chars())
                else:
                    mutated[key] = []
    
    elif mutation_strategy == "replace_field":
        if mutated:
            key = random.choice(list(mutated.keys()))
            
            if key == "name":
                mutated[key] = grammar.generate_name()
            elif key == "email":
                mutated[key] = grammar.generate_email()
            elif key == "age":
                mutated[key] = grammar.generate_age()
            elif key == "zipcode":
                mutated[key] = grammar.generate_zipcode()
            elif key == "hobbies":
                mutated[key] = grammar.generate_hobbies()
            elif key == "username":
                mutated[key] = grammar.generate_username()
            elif key == "password":
                mutated[key] = grammar.generate_password()
            else:
                mutated[key] = grammar.generate_random_chars()
    
    if "memleak" in mutated and random.random() < 0.1:
        mutated["memleak"] = True
    
    if "delay" in mutated and random.random() < 0.1:
        mutated["delay"] = random.uniform(0.1, 3.0)
    
    if random.random() < 0.05:
        sql_patterns = [
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "' UNION SELECT * FROM users; --",
            "' DELETE FROM users WHERE '1'='1",
            f"{grammar.generate_random_chars(3, 8)}' OR '1'='1"
        ]
        
        key = random.choice(list(mutated.keys())) if mutated else "name"
        if isinstance(mutated.get(key, ""), str):
            mutated[key] = random.choice(sql_patterns)
    
    result = creator.Individual(mutated)
    return result

def crossover_payloads(parent1: Dict[str, Any], parent2: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    child1 = {}
    child2 = {}
    
    all_keys = set(list(parent1.keys()) + list(parent2.keys()))
    
    for key in all_keys:
        if key in parent1 and key in parent2:
            if random.random() < 0.5:
                child1[key] = parent1[key]
                child2[key] = parent2[key]
            else:
                child1[key] = parent2[key]
                child2[key] = parent1[key]
        elif key in parent1:
            if random.random() < 0.7:
                child1[key] = parent1[key]
            if random.random() < 0.3:
                child2[key] = parent1[key]
        elif key in parent2:
            if random.random() < 0.7:
                child2[key] = parent2[key]
            if random.random() < 0.3:
                child1[key] = parent2[key]
    
    if random.random() < 0.1:
        extra_field = grammar.generate_random_chars(3, 8)
        extra_value = grammar.generate_random_chars(3, 15)
        child1[extra_field] = extra_value
    
    if random.random() < 0.1:
        extra_field = grammar.generate_random_chars(3, 8)
        extra_value = grammar.generate_random_chars(3, 15)
        child2[extra_field] = extra_value
    
    if not child1:
        child1 = {"name": grammar.generate_name()}
    
    if not child2:
        child2 = {"name": grammar.generate_name()}
    
    result1 = creator.Individual(child1)
    result2 = creator.Individual(child2)
    return result1, result2

def save_generation_stats(stats: Dict[str, List[float]], generation: int, directory: str) -> None:
    filename = os.path.join(directory, f"generation_{generation:04d}_stats.json")
    
    with open(filename, 'w') as f:
        json.dump({
            "generation": generation,
            "timestamp": datetime.now().isoformat(),
            "stats": stats
        }, f, indent=2)
    
    summary_file = os.path.join(directory, "evolution_stats.json")
    
    all_stats = {}
    if os.path.exists(summary_file):
        with open(summary_file, 'r') as f:
            try:
                all_stats = json.load(f)
            except json.JSONDecodeError:
                pass
    
    for key, values in stats.items():
        if key not in all_stats:
            all_stats[key] = []
        all_stats[key].extend(values)
    
    with open(summary_file, 'w') as f:
        json.dump(all_stats, f, indent=2)

def save_best_payloads(population: List[Dict[str, Any]], fitnesses: List[float], 
                      directory: str, top_n: int = 10) -> None:
    combined = list(zip(population, fitnesses))
    combined.sort(key=lambda x: x[1], reverse=True)
    
    top_payloads = combined[:top_n]
    
    filename = os.path.join(directory, f"best_payloads_{int(time.time())}.json")
    
    with open(filename, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "payloads": [
                {
                    "payload": payload,
                    "fitness": fitness
                }
                for payload, fitness in top_payloads
            ]
        }, f, indent=2)

def parse_arguments():
    parser = argparse.ArgumentParser(description='Genetic algorithm API tester')
    
    parser.add_argument('--population', type=int, default=POPULATION_SIZE,
                        help=f'Population size (default: {POPULATION_SIZE})')
    parser.add_argument('--generations', type=int, default=NUM_GENERATIONS,
                        help=f'Number of generations (default: {NUM_GENERATIONS})')
    parser.add_argument('--crossover', type=float, default=CROSSOVER_PROBABILITY,
                        help=f'Crossover probability (default: {CROSSOVER_PROBABILITY})')
    parser.add_argument('--mutation', type=float, default=MUTATION_PROBABILITY,
                        help=f'Mutation probability (default: {MUTATION_PROBABILITY})')
    
    return parser.parse_args()

def main():
    args = parse_arguments()
    
    logger.info(f"Starting genetic algorithm API tester with population={args.population}, "
                f"generations={args.generations}")
    
    output_dir = setup_output_directory()
    logger.info(f"Results will be saved to: {output_dir}")
    
    creator.create("FitnessMax", base.Fitness, weights=(1.0,))
    creator.create("Individual", dict, fitness=creator.FitnessMax)
    
    toolbox = base.Toolbox()
    
    # Make sure to create DEAP Individuals, not just dicts
    toolbox.register("individual", lambda: creator.Individual(grammar.generate_candidate()))
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)
    
    toolbox.register("evaluate", evaluate_individual)
    toolbox.register("mate", crossover_payloads)
    toolbox.register("mutate", mutate_payload)
    toolbox.register("select", tools.selTournament, tournsize=TOURNAMENT_SIZE)
    
    pop = toolbox.population(n=args.population)
    
    logger.info("Evaluating initial population")
    fitnesses = list(map(toolbox.evaluate, pop))
    for ind, fit in zip(pop, fitnesses):
        ind.fitness.values = fit
    
    stats = tools.Statistics(lambda ind: ind.fitness.values[0])
    stats.register("avg", statistics.mean)
    stats.register("min", min)
    stats.register("max", max)
    
    logger.info(f"Starting evolution for {args.generations} generations")
    start_time = time.time()
    
    all_gen_stats = {}
    best_individual = None
    best_fitness = 0
    
    for gen in range(args.generations):
        gen_start_time = time.time()
        
        offspring = toolbox.select(pop, len(pop))
        offspring = list(map(toolbox.clone, offspring))
        
        for i in range(1, len(offspring), 2):
            if random.random() < args.crossover:
                offspring[i-1], offspring[i] = toolbox.mate(offspring[i-1], offspring[i])
                del offspring[i-1].fitness.values
                del offspring[i].fitness.values
        
        for i in range(len(offspring)):
            if random.random() < args.mutation:
                offspring[i] = toolbox.mutate(offspring[i])
                del offspring[i].fitness.values
        
        invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
        fitnesses = map(toolbox.evaluate, invalid_ind)
        for ind, fit in zip(invalid_ind, fitnesses):
            ind.fitness.values = fit
        
        pop = toolbox.select(offspring, k=len(pop))
        
        gen_stats = stats.compile(pop)
        logger.info(f"Generation {gen+1}: {gen_stats}")
        
        for key, value in gen_stats.items():
            if key not in all_gen_stats:
                all_gen_stats[key] = []
            all_gen_stats[key].append(value)
        
        save_generation_stats(
            {key: [values[gen]] for key, values in all_gen_stats.items()},
            gen+1, 
            os.path.join(output_dir, "stats")
        )
        
        gen_best = tools.selBest(pop, 1)[0]
        gen_best_fitness = gen_best.fitness.values[0]
        
        if gen_best_fitness > best_fitness:
            best_individual = gen_best
            best_fitness = gen_best_fitness
            
            logger.info(f"New best individual with fitness {best_fitness}: {json.dumps(best_individual)}")
        
        current_fitnesses = [ind.fitness.values[0] for ind in pop]
        save_best_payloads(
            pop, current_fitnesses,
            os.path.join(output_dir, "payloads"),
            top_n=10
        )
        
        gen_time = time.time() - gen_start_time
        logger.info(f"Generation {gen+1} completed in {gen_time:.2f} seconds")
    
    logger.info("Saving tracked payloads")
    payload_tracker.save_to_disk()
    
    payload_tracker.print_summary()
    
    total_time = time.time() - start_time
    logger.info(f"Evolution completed in {total_time:.2f} seconds")
    
    return pop, best_individual

if __name__ == "__main__":
    main()
