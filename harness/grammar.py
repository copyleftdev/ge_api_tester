"""
Grammar module for generating API payloads
Enhanced to work with the more realistic API endpoints
"""
import random
import string
import json
import time

# --- Character Generation Functions ---
def generate_random_chars(min_length=3, max_length=10):
    """Generate a random string of characters."""
    length = random.randint(min_length, max_length)
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))

def generate_random_email():
    """Generate a random email address."""
    username = generate_random_chars(3, 8)
    domain = generate_random_chars(3, 7)
    tld = random.choice(['com', 'org', 'net', 'io', 'co'])
    
    # 20% chance of generating an invalid email
    if random.random() < 0.2:
        # Apply different error patterns
        error_type = random.randint(0, 3)
        if error_type == 0:
            # Missing @ symbol
            return f"{username}{domain}.{tld}"
        elif error_type == 1:
            # Missing domain
            return f"{username}@.{tld}"
        elif error_type == 2:
            # Strange characters
            return f"{username}@{domain}.{tld}!#"
        else:
            # Double @
            return f"{username}@@{domain}.{tld}"
    
    return f"{username}@{domain}.{tld}"

def generate_random_zipcode():
    """Generate a random US zipcode."""
    # 15% chance to generate the special 90210 zipcode (triggers server error)
    if random.random() < 0.15:
        return '90210'
    
    # 10% chance to generate an invalid zipcode
    if random.random() < 0.10:
        # Invalid formats
        formats = [
            '123',                 # Too short
            '1234567',             # Too long
            'ABC12',               # Letters instead of numbers
            '12345-123',           # Invalid extension format
            '123456-1234',         # Too many digits
            '12345-'               # Incomplete extended format
        ]
        return random.choice(formats)
    
    # Standard 5-digit zipcode 70% of the time
    if random.random() < 0.7:
        return ''.join([str(random.randint(0, 9)) for _ in range(5)])
    
    # Extended zipcode 30% of the time
    zipcode = ''.join([str(random.randint(0, 9)) for _ in range(5)])
    extension = ''.join([str(random.randint(0, 9)) for _ in range(4)])
    return f"{zipcode}-{extension}"

def generate_random_age():
    """Generate a random age value."""
    # Different distributions of age to test various conditions
    age_types = random.randint(0, 4)
    
    if age_types == 0:  # Valid age (0-120)
        return random.randint(0, 120)
    elif age_types == 1:  # Negative age (invalid)
        return -random.randint(1, 100)
    elif age_types == 2:  # Very large age (invalid)
        return random.randint(121, 1000)
    elif age_types == 3:  # Age as string that can be parsed (sometimes valid)
        age = random.randint(0, 150)
        return str(age)
    else:  # Age as unparseable string (invalid)
        return generate_random_chars()

def generate_random_hobbies():
    """Generate a list of random hobbies."""
    common_hobbies = [
        "reading", "writing", "gaming", "cooking", "hiking", 
        "programming", "music", "movies", "sports", "photography",
        "gardening", "painting", "travel", "fishing", "swimming",
        "biking", "running", "yoga", "meditation", "dancing"
    ]
    
    restricted_hobbies = [
        "hacking", "fraud", "illegal activities", 
        "phishing", "spamming", "scamming"
    ]
    
    num_hobbies = random.randint(1, 5)
    hobbies = []
    
    # 15% chance to include a restricted hobby
    if random.random() < 0.15:
        hobbies.append(random.choice(restricted_hobbies))
        num_hobbies -= 1
    
    # Fill the rest with common hobbies
    available_hobbies = common_hobbies.copy()
    for _ in range(num_hobbies):
        if not available_hobbies:
            break
        hobby = random.choice(available_hobbies)
        available_hobbies.remove(hobby)
        hobbies.append(hobby)
    
    # 10% chance to have an invalid hobbies format (not a list)
    if random.random() < 0.1:
        return ",".join(hobbies)  # Return as comma-separated string
    
    return hobbies

def generate_auth_payload():
    """Generate an authentication payload."""
    payload = {
        "username": generate_username() if random.random() < 0.5 else generate_email(),
        "password": generate_password()
    }
    
    # 10% chance to add extra fields
    if random.random() < 0.1:
        extra_fields = ["remember_me", "token_lifetime", "client_id"]
        num_extras = random.randint(1, len(extra_fields))
        
        for _ in range(num_extras):
            if not extra_fields:
                break
            field = random.choice(extra_fields)
            extra_fields.remove(field)
            
            if field == "remember_me":
                payload[field] = random.choice([True, False])
            elif field == "token_lifetime":
                payload[field] = random.choice([300, 900, 1800, 3600, 86400])
            elif field == "client_id":
                payload[field] = generate_random_chars(10, 20)
    
    return payload

def generate_user_payload():
    """Generate a payload for user creation/update."""
    # Start with basic required name field
    payload = {
        "name": generate_random_chars(3, 15)
    }
    
    # 10% chance to make name too long (invalid)
    if random.random() < 0.1:
        payload["name"] = generate_random_chars(51, 100)
    
    # 10% chance to make name too short (invalid)
    if random.random() < 0.1:
        payload["name"] = generate_random_chars(1, 2)
    
    # 5% chance to include a SQL injection attempt in name
    if random.random() < 0.05:
        sql_patterns = [
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "' UNION SELECT * FROM users; --",
            "' DELETE FROM users WHERE '1'='1",
            f"{generate_random_chars(3, 8)}' OR '1'='1"
        ]
        payload["name"] = random.choice(sql_patterns)
    
    # 80% chance to include age
    if random.random() < 0.8:
        payload["age"] = generate_random_age()
    
    # 70% chance to include email
    if random.random() < 0.7:
        payload["email"] = generate_random_email()
    
    # 60% chance to include zipcode
    if random.random() < 0.6:
        payload["zipcode"] = generate_random_zipcode()
    
    # 50% chance to include hobbies
    if random.random() < 0.5:
        payload["hobbies"] = generate_random_hobbies()
    
    # 10% chance to include memory leak flag
    if random.random() < 0.1:
        payload["memleak"] = True
    
    return payload

def generate_endpoint_specific_payload():
    """Generate payloads specific to various API endpoints."""
    endpoints = [
        "auth",
        "users",
        "predict",  # Legacy endpoint
        "health"
    ]
    
    selected_endpoint = random.choice(endpoints)
    
    if selected_endpoint == "auth":
        return generate_auth_payload()
    elif selected_endpoint == "users":
        return generate_user_payload()
    elif selected_endpoint == "predict":
        return generate_legacy_payload()
    else:  # health endpoint doesn't need a payload
        return {}

def generate_legacy_payload():
    """Generate a payload compatible with the legacy /predict endpoint."""
    payload = {
        "name": generate_random_chars()
    }
    
    # 70% chance to include age
    if random.random() < 0.7:
        payload["age"] = generate_random_age()
    
    # 20% chance to include other fields
    if random.random() < 0.2:
        # Legacy field for testing specific behaviors
        payload["created"] = random.choice([True, False])
    
    if random.random() < 0.2:
        # Another legacy field
        payload["accepted"] = random.choice([True, False])
    
    # 10% chance to include a delay field
    if random.random() < 0.1:
        payload["delay"] = random.uniform(0.1, 2.0)
    
    return payload

def generate_metadata_payload():
    """Generate metadata that might be used in headers or query parameters."""
    # This could be used for things like pagination, sorting, etc.
    metadata = {}
    
    # 30% chance to include pagination info
    if random.random() < 0.3:
        metadata["page"] = random.randint(1, 10)
        metadata["limit"] = random.choice([10, 20, 50, 100, 200])  # Test various page sizes including invalid ones
    
    # 20% chance to include ordering info
    if random.random() < 0.2:
        # Valid and invalid sort fields
        fields = ["name", "age", "email", "created_at", "invalid_field", "'; DROP TABLE users; --"]
        metadata["sort_by"] = random.choice(fields)
        metadata["sort_order"] = random.choice(["asc", "desc", "invalid"])
    
    return metadata

def generate_candidate():
    """Generate a candidate JSON payload for the API."""
    # Decide which type of payload to generate
    payload_type = random.randint(0, 5)
    
    # User creation/update payload (most common)
    if payload_type <= 3:
        return generate_user_payload()
    
    # Authentication payload
    elif payload_type == 4:
        return generate_auth_payload()
    
    # Legacy payload
    else:
        return generate_legacy_payload()
    
    # Note: We don't use generate_endpoint_specific_payload directly
    # as it might create empty payloads which won't be useful for testing

def generate_name():
    """Generate a random name."""
    first_names = [
        "John", "Jane", "Michael", "Emma", "William", "Olivia", "James", 
        "Sophia", "Alexander", "Ava", "David", "Mia", "Joseph", "Isabella", 
        "Daniel", "Charlotte", "Matthew", "Amelia", "Andrew", "Harper"
    ]
    last_names = [
        "Smith", "Johnson", "Williams", "Jones", "Brown", "Davis", "Miller", 
        "Wilson", "Moore", "Taylor", "Anderson", "Thomas", "Jackson", "White", 
        "Harris", "Martin", "Thompson", "Garcia", "Martinez", "Robinson"
    ]
    
    # 90% chance to generate a valid name
    if random.random() < 0.9:
        return f"{random.choice(first_names)} {random.choice(last_names)}"
    else:
        # Generate a random string for invalid cases
        return generate_random_chars(2, 20)

def generate_email():
    """Generate a random, valid email address."""
    # Create a valid email directly instead of using generate_random_email which has invalid cases
    username = generate_random_chars(3, 8)
    domain = generate_random_chars(3, 7)
    tld = random.choice(['com', 'org', 'net', 'io', 'co'])
    return f"{username}@{domain}.{tld}"

def generate_age():
    """Generate a random, valid age (0-120)."""
    # Only return valid ages for the test cases
    return random.randint(0, 120)

def generate_zipcode():
    """Generate a random, valid US zipcode (5 digits)."""
    # Generate only valid 5-digit zipcodes for test cases
    return ''.join([str(random.randint(0, 9)) for _ in range(5)])

def generate_hobbies():
    """Generate a list of random hobbies."""
    common_hobbies = [
        "reading", "writing", "gaming", "cooking", "hiking", 
        "programming", "music", "movies", "sports", "photography",
        "gardening", "painting", "travel", "fishing", "swimming",
        "biking", "running", "yoga", "meditation", "dancing"
    ]
    
    num_hobbies = random.randint(1, 5)
    hobbies = []
    
    # Select random hobbies without duplicates
    available_hobbies = common_hobbies.copy()
    for _ in range(num_hobbies):
        if not available_hobbies:
            break
        hobby = random.choice(available_hobbies)
        available_hobbies.remove(hobby)
        hobbies.append(hobby)
    
    return hobbies

def generate_username():
    """Generate a random username."""
    # Username patterns
    patterns = [
        f"{generate_random_chars(3, 8)}",
        f"{generate_random_chars(2, 5)}_{generate_random_chars(2, 5)}",
        f"{generate_random_chars(3, 6)}{random.randint(1, 999)}"
    ]
    return random.choice(patterns)

def generate_password():
    """Generate a random password."""
    # Password patterns with varying complexity
    length = random.randint(8, 16)
    chars = string.ascii_letters + string.digits + "!@#$%^&*()"
    return ''.join(random.choice(chars) for _ in range(length))

def generate_random_payload():
    """Generate a random API payload with mixed fields."""
    # Start with either a user or auth payload as base
    if random.random() < 0.5:
        payload = generate_user_payload()
    else:
        payload = generate_auth_payload()
        
    # 30% chance to add some extra random fields
    if random.random() < 0.3:
        extra_fields = ["timestamp", "version", "device", "location", "status"]
        num_extras = random.randint(1, 3)
        
        for _ in range(num_extras):
            if not extra_fields:
                break
            field = random.choice(extra_fields)
            extra_fields.remove(field)
            
            if field == "timestamp":
                payload[field] = int(time.time())
            elif field == "version":
                payload[field] = f"{random.randint(1, 5)}.{random.randint(0, 9)}.{random.randint(0, 9)}"
            elif field == "device":
                devices = ["mobile", "desktop", "tablet", "api"]
                payload[field] = random.choice(devices)
            elif field == "location":
                payload[field] = f"{random.randint(-90, 90)},{random.randint(-180, 180)}"
            elif field == "status":
                statuses = ["active", "pending", "inactive", "deleted"]
                payload[field] = random.choice(statuses)
    
    return payload

def crossover_payloads(payload1, payload2):
    """Combine fields from two parent payloads to create a child payload."""
    child = {}
    
    # Get all unique keys from both parents
    all_keys = set(list(payload1.keys()) + list(payload2.keys()))
    
    for key in all_keys:
        # For each key, randomly choose which parent to inherit from
        if key in payload1 and key in payload2:
            # If both parents have the key, 50% chance to choose either
            child[key] = payload1[key] if random.random() < 0.5 else payload2[key]
        elif key in payload1:
            # 70% chance to inherit from parent1 if only parent1 has the key
            if random.random() < 0.7:
                child[key] = payload1[key]
        elif key in payload2:
            # 70% chance to inherit from parent2 if only parent2 has the key
            if random.random() < 0.7:
                child[key] = payload2[key]
    
    return child

def mutate_payload(payload):
    """Randomly mutate a payload by adding, removing, or changing fields."""
    # Create a copy to avoid modifying the original
    mutated = payload.copy()
    
    # Pick a mutation type:
    # 0: Add a new field
    # 1: Remove a field
    # 2: Modify an existing field
    mutation_type = random.randint(0, 2)
    
    if mutation_type == 0 or not mutated:  # Add (or must add if empty)
        # Possible new fields to add
        new_fields = {
            "name": generate_name,
            "email": generate_email,
            "age": generate_age,
            "zipcode": generate_zipcode,
            "hobbies": generate_hobbies,
            "username": generate_username,
            "password": generate_password,
            "timestamp": lambda: int(time.time())
        }
        
        # Remove fields that already exist
        for existing in list(mutated.keys()):
            if existing in new_fields:
                del new_fields[existing]
        
        if new_fields:
            # Pick a random field to add
            field_name = random.choice(list(new_fields.keys()))
            field_generator = new_fields[field_name]
            mutated[field_name] = field_generator()
    
    elif mutation_type == 1 and mutated:  # Remove
        # Pick a random field to remove
        field_to_remove = random.choice(list(mutated.keys()))
        del mutated[field_to_remove]
    
    elif mutation_type == 2 and mutated:  # Modify
        # Pick a random field to modify
        field_to_modify = random.choice(list(mutated.keys()))
        
        # Define how to modify each type of field
        if field_to_modify == "name":
            mutated[field_to_modify] = generate_name()
        elif field_to_modify == "email":
            mutated[field_to_modify] = generate_email()
        elif field_to_modify == "age":
            mutated[field_to_modify] = generate_age()
        elif field_to_modify == "zipcode":
            mutated[field_to_modify] = generate_zipcode()
        elif field_to_modify == "hobbies":
            mutated[field_to_modify] = generate_hobbies()
        elif field_to_modify == "username":
            mutated[field_to_modify] = generate_username()
        elif field_to_modify == "password":
            mutated[field_to_modify] = generate_password()
        else:
            # For any other field, replace with a random string
            mutated[field_to_modify] = generate_random_chars()
    
    return mutated

if __name__ == "__main__":
    # Generate a few examples for testing
    for _ in range(5):
        print(json.dumps(generate_candidate(), indent=2))
