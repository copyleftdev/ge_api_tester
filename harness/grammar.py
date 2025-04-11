import random
import string
import json
import time

def generate_random_chars(min_length=3, max_length=10):
    length = random.randint(min_length, max_length)
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))

def generate_random_email():
    username = generate_random_chars(3, 8)
    domain = generate_random_chars(3, 7)
    tld = random.choice(['com', 'org', 'net', 'io', 'co'])
    
    if random.random() < 0.2:
        error_type = random.randint(0, 3)
        if error_type == 0:
            return f"{username}{domain}.{tld}"
        elif error_type == 1:
            return f"{username}@.{tld}"
        elif error_type == 2:
            return f"{username}@{domain}.{tld}!#"
        else:
            return f"{username}@@{domain}.{tld}"
    
    return f"{username}@{domain}.{tld}"

def generate_random_zipcode():
    if random.random() < 0.15:
        return '90210'
    
    if random.random() < 0.10:
        formats = [
            '123',                 
            '1234567',             
            'ABC12',               
            '12345-123',           
            '123456-1234',         
            '12345-'               
        ]
        return random.choice(formats)
    
    if random.random() < 0.7:
        return ''.join([str(random.randint(0, 9)) for _ in range(5)])
    
    zipcode = ''.join([str(random.randint(0, 9)) for _ in range(5)])
    extension = ''.join([str(random.randint(0, 9)) for _ in range(4)])
    return f"{zipcode}-{extension}"

def generate_random_age():
    age_types = random.randint(0, 4)
    
    if age_types == 0:  
        return random.randint(0, 120)
    elif age_types == 1:  
        return -random.randint(1, 100)
    elif age_types == 2:  
        return random.randint(121, 1000)
    elif age_types == 3:  
        age = random.randint(0, 150)
        return str(age)
    else:  
        return generate_random_chars()

def generate_random_hobbies():
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
    
    if random.random() < 0.15:
        hobbies.append(random.choice(restricted_hobbies))
        num_hobbies -= 1
    
    available_hobbies = common_hobbies.copy()
    for _ in range(num_hobbies):
        if not available_hobbies:
            break
        hobby = random.choice(available_hobbies)
        available_hobbies.remove(hobby)
        hobbies.append(hobby)
    
    return hobbies

def generate_auth_payload():
    payload = {
        "username": generate_username() if random.random() < 0.5 else generate_email(),
        "password": generate_password()
    }
    
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
    payload = {
        "name": generate_name()
    }
    
    if random.random() < 0.1:
        payload["name"] = generate_random_chars(1, 2)
    
    if random.random() < 0.05:
        sql_patterns = [
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "' UNION SELECT * FROM users; --",
            "' DELETE FROM users WHERE '1'='1",
            f"{generate_random_chars(3, 8)}' OR '1'='1"
        ]
        payload["name"] = random.choice(sql_patterns)
    
    if random.random() < 0.8:
        payload["age"] = generate_random_age()
    
    if random.random() < 0.7:
        payload["email"] = generate_random_email()
    
    if random.random() < 0.6:
        payload["zipcode"] = generate_random_zipcode()
    
    if random.random() < 0.5:
        payload["hobbies"] = generate_random_hobbies()
    
    if random.random() < 0.1:
        payload["memleak"] = True
    
    return payload

def generate_endpoint_specific_payload():
    endpoints = [
        "auth",
        "users",
        "predict", 
        "health"
    ]
    
    selected_endpoint = random.choice(endpoints)
    
    if selected_endpoint == "auth":
        return generate_auth_payload()
    elif selected_endpoint == "users":
        return generate_user_payload()
    elif selected_endpoint == "predict":
        return generate_legacy_payload()
    else:
        return {}

def generate_legacy_payload():
    payload = {
        "name": generate_random_chars()
    }
    
    if random.random() < 0.7:
        payload["age"] = generate_random_age()
    
    if random.random() < 0.2:
        payload["created"] = random.choice([True, False])
    
    if random.random() < 0.2:
        payload["accepted"] = random.choice([True, False])
    
    if random.random() < 0.1:
        payload["delay"] = random.uniform(0.1, 2.0)
    
    return payload

def generate_metadata_payload():
    metadata = {}
    
    if random.random() < 0.3:
        metadata["page"] = random.randint(1, 10)
        metadata["limit"] = random.choice([10, 20, 50, 100, 200])
    
    if random.random() < 0.2:
        fields = ["name", "age", "email", "created_at", "invalid_field", "'; DROP TABLE users; --"]
        metadata["sort_by"] = random.choice(fields)
        metadata["sort_order"] = random.choice(["asc", "desc", "invalid"])
    
    return metadata

def generate_candidate():
    payload_type = random.randint(0, 5)
    
    if payload_type <= 3:
        return generate_user_payload()
    
    elif payload_type == 4:
        return generate_auth_payload()
    
    else:
        return generate_legacy_payload()

def generate_name():
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
    
    if random.random() < 0.9:
        return f"{random.choice(first_names)} {random.choice(last_names)}"
    else:
        return generate_random_chars(2, 20)

def generate_email():
    username = generate_random_chars(3, 8)
    domain = generate_random_chars(3, 7)
    tld = random.choice(['com', 'org', 'net', 'io', 'co'])
    return f"{username}@{domain}.{tld}"

def generate_age():
    return random.randint(0, 120)

def generate_zipcode():
    return ''.join([str(random.randint(0, 9)) for _ in range(5)])

def generate_hobbies():
    common_hobbies = [
        "reading", "writing", "gaming", "cooking", "hiking", 
        "programming", "music", "movies", "sports", "photography",
        "gardening", "painting", "travel", "fishing", "swimming",
        "biking", "running", "yoga", "meditation", "dancing"
    ]
    
    num_hobbies = random.randint(1, 5)
    hobbies = []
    
    available_hobbies = common_hobbies.copy()
    for _ in range(num_hobbies):
        if not available_hobbies:
            break
        hobby = random.choice(available_hobbies)
        available_hobbies.remove(hobby)
        hobbies.append(hobby)
    
    return hobbies

def generate_username():
    patterns = [
        f"{generate_random_chars(3, 8)}",
        f"{generate_random_chars(2, 5)}_{generate_random_chars(2, 5)}",
        f"{generate_random_chars(3, 6)}{random.randint(1, 999)}"
    ]
    return random.choice(patterns)

def generate_password():
    length = random.randint(8, 16)
    chars = string.ascii_letters + string.digits + "!@#$%^&*()"
    return ''.join(random.choice(chars) for _ in range(length))

def generate_random_payload():
    if random.random() < 0.5:
        payload = generate_user_payload()
    else:
        payload = generate_auth_payload()
        
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
    child = {}
    
    all_keys = set(list(payload1.keys()) + list(payload2.keys()))
    
    for key in all_keys:
        if key in payload1 and key in payload2:
            child[key] = payload1[key] if random.random() < 0.5 else payload2[key]
        elif key in payload1:
            if random.random() < 0.7:
                child[key] = payload1[key]
        elif key in payload2:
            if random.random() < 0.7:
                child[key] = payload2[key]
    
    return child

def mutate_payload(payload):
    mutated = payload.copy()
    
    mutation_type = random.randint(0, 2)
    
    if mutation_type == 0 or not mutated:
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
        
        for existing in list(mutated.keys()):
            if existing in new_fields:
                del new_fields[existing]
        
        if new_fields:
            field_name = random.choice(list(new_fields.keys()))
            field_generator = new_fields[field_name]
            mutated[field_name] = field_generator()
    
    elif mutation_type == 1 and mutated:
        field_to_remove = random.choice(list(mutated.keys()))
        del mutated[field_to_remove]
    
    elif mutation_type == 2 and mutated:
        field_to_modify = random.choice(list(mutated.keys()))
        
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
            mutated[field_to_modify] = generate_random_chars()
    
    return mutated

if __name__ == "__main__":
    for _ in range(5):
        print(json.dumps(generate_candidate(), indent=2))
