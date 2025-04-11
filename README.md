# Genetic Evolution API Tester

This project demonstrates using a genetic algorithm (GA) powered by the DEAP library to automatically generate and evolve test payloads for a simple Flask API. The entire setup runs within Docker containers orchestrated by Docker Compose, allowing the API and the testing harness to run in parallel and isolated environments.

## Project Structure

```plaintext
ge_api_tester/
├── api/                # Contains the Flask API server code
│   ├── api_server.py   # The Flask application script
│   └── Dockerfile      # Dockerfile to build the API image
├── harness/            # Contains the evolution engine code
│   ├── evolve_tester.py # Main GA script using DEAP
│   ├── grammar.py      # Defines payload structure rules
│   ├── utils.py        # Evaluation function and helpers
│   └── Dockerfile      # Dockerfile to build the harness image
├── docker-compose.yml  # Docker Compose configuration
├── requirements.txt    # Python dependencies for both services
└── README.md           # This documentation file
```

## How it Works

1.  **API Service (`api`)**: A basic Flask server listens on port 5000 (inside the container, mapped to port 5000 on the host). It has a `/predict` endpoint that accepts POST requests with JSON data. It includes basic validation and simulates errors under certain conditions.
2.  **Harness Service (`harness`)**: This container runs a Python script (`evolve_tester.py`) using the DEAP library.
    * It generates initial JSON payloads based on rules defined in `grammar.py`.
    * It sends these payloads to the `api` service's `/predict` endpoint (using the service name `api` for discovery within the Docker network).
    * The `utils.py` script evaluates the API's response (status code, content) and assigns a "fitness" score. Higher scores are given for payloads that trigger errors (5xx status) or interesting behavior (specific zip codes, diverse hobbies).
    * The GA uses selection, crossover, and mutation operators to evolve the population of payloads over several generations, aiming to maximize the fitness score.
3.  **Docker Compose**: Manages both services, builds the necessary Docker images, sets up networking between containers, and handles startup order (`harness` starts after `api`).

## Prerequisites

* Docker: [Install Docker](https://docs.docker.com/engine/install/)
* Docker Compose: Usually included with Docker Desktop. If not, [Install Docker Compose](https://docs.docker.com/compose/install/)

## Setup and Running

1.  **Clone or Download:** Obtain the project files and place them in a directory named `ge_api_tester`.
2.  **Navigate:** Open a terminal or command prompt and change to the `ge_api_tester` directory.
    ```bash
    cd path/to/ge_api_tester
    ```
3.  **Build and Run:** Use Docker Compose to build the images and start the containers.
    ```bash
    docker-compose up --build
    ```
    * `--build`: Forces Docker Compose to rebuild the images if they don't exist or if the source files/Dockerfiles have changed.
4.  **Observe:** Watch the terminal output. You will see logs from both the `api` service (logging incoming requests) and the `harness` service (logging the progress of the genetic algorithm, including fitness statistics per generation and the best payload found).
5.  **Stop:** Press `CTRL+C` in the terminal where `docker-compose up` is running to stop the containers.
6.  **Cleanup (Optional):** To remove the containers, networks, and volumes created by Compose:
    ```bash
    docker-compose down
    ```

## Customization

* **API Logic:** Modify `api/api_server.py` to implement different endpoints, validation rules, or error conditions.
* **Payload Grammar:** Adjust `harness/grammar.py` to change the structure and possible values of the generated JSON payloads.
* **Fitness Evaluation:** Update the `evaluate_candidate` function in `harness/utils.py` to change how payloads are scored based on the API's responses.
* **GA Parameters:** Tune parameters like `population_size`, `num_generations`, `crossover_prob`, and `mutation_prob` in `harness/evolve_tester.py`.
* **Genetic Operators:** Implement more sophisticated `custom_crossover` and `custom_mutate` functions in `harness/evolve_tester.py` suitable for dictionary-based individuals.
