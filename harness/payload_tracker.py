import json
import os
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PayloadTracker:
    def __init__(self, max_tracked_items=100, output_dir="./tracked_payloads"):
        self.output_dir = output_dir
        self.max_tracked_items = max_tracked_items
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        self.high_fitness_payloads = []
        self.server_errors = []
        self.validation_errors = []
        self.slow_responses = []
        self.timeouts = []
        self.sql_injection_hits = []
        self.memory_issues = []
        self.auth_issues = []
        self.auth_tokens = []
        
        self._auth_token = None
        
        if not os.path.isabs(output_dir):
            self.abs_output_dir = os.path.abspath(output_dir)
        else:
            self.abs_output_dir = output_dir
        
        logger.info(f"PayloadTracker initialized with output directory: {output_dir}")
    
    def _add_tracked_item(self, category: List[Dict[str, Any]], payload: Dict[str, Any], 
                          response_info: Dict[str, Any], extra_info: Optional[Dict[str, Any]] = None) -> None:
        timestamp = datetime.now().isoformat()
        
        tracked_item = {
            "timestamp": timestamp,
            "payload": payload,
            "response": response_info,
        }
        
        if extra_info:
            tracked_item.update(extra_info)
        
        category.append(tracked_item)
        if len(category) > self.max_tracked_items:
            category.pop(0)
    
    def track_high_fitness(self, payload: Dict[str, Any], response_info: Dict[str, Any], 
                           fitness_score: float) -> None:
        self._add_tracked_item(
            self.high_fitness_payloads, 
            payload, 
            response_info,
            {"fitness_score": fitness_score}
        )
        logger.debug(f"Tracked high fitness payload with score: {fitness_score}")
    
    def track_server_error(self, payload: Dict[str, Any], response_info: Dict[str, Any]) -> None:
        self._add_tracked_item(self.server_errors, payload, response_info)
        logger.debug(f"Tracked server error with status code: {response_info.get('status_code')}")
    
    def track_validation_error(self, payload: Dict[str, Any], response_info: Dict[str, Any]) -> None:
        self._add_tracked_item(self.validation_errors, payload, response_info)
        logger.debug(f"Tracked validation error with status code: {response_info.get('status_code')}")
    
    def track_slow_response(self, payload: Dict[str, Any], response_info: Dict[str, Any], 
                            response_time: float) -> None:
        self._add_tracked_item(
            self.slow_responses, 
            payload, 
            response_info,
            {"response_time": response_time}
        )
        logger.debug(f"Tracked slow response with time: {response_time}s")
    
    def track_timeout(self, payload: Dict[str, Any], response_info: Dict[str, Any]) -> None:
        self._add_tracked_item(self.timeouts, payload, response_info)
        logger.debug("Tracked timeout")
    
    def track_sql_injection(self, payload: Dict[str, Any], response_info: Dict[str, Any] = None) -> None:
        self._add_tracked_item(self.sql_injection_hits, payload, response_info or {})
        logger.debug("Tracked potential SQL injection")
    
    def track_memory_issue(self, payload: Dict[str, Any], response_info: Dict[str, Any] = None) -> None:
        self._add_tracked_item(self.memory_issues, payload, response_info or {})
        logger.debug("Tracked memory issue")
    
    def track_auth_issue(self, payload: Dict[str, Any], response_info: Dict[str, Any]) -> None:
        self._add_tracked_item(self.auth_issues, payload, response_info)
        logger.debug("Tracked authentication issue")
    
    def track_auth_token_update(self, token, auth_data) -> None:
        timestamp = datetime.now().isoformat()
        
        token_info = {
            "timestamp": timestamp,
            "token": token,
            "auth_data": auth_data
        }
        
        self.auth_tokens.append(token_info)
        self._auth_token = token
        
        logger.debug("Tracked auth token update")
    
    def get_auth_token(self) -> Optional[str]:
        return self._auth_token
    
    def set_auth_token(self, token: str) -> None:
        self._auth_token = token
        logger.debug("Set auth token")
    
    def save_to_disk(self) -> Dict[str, str]:
        saved_files = {}
        timestamp = int(time.time())
        
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        
        if self.high_fitness_payloads:
            file_path = os.path.join(self.output_dir, f"high_fitness_{timestamp}.json")
            with open(file_path, 'w') as f:
                json.dump(self.high_fitness_payloads, f, indent=2)
            saved_files['high_fitness'] = file_path
            logger.info(f"Saved {len(self.high_fitness_payloads)} high_fitness payloads to {file_path}")
        
        if self.server_errors:
            file_path = os.path.join(self.output_dir, f"server_errors_{timestamp}.json")
            with open(file_path, 'w') as f:
                json.dump(self.server_errors, f, indent=2)
            saved_files['server_errors'] = file_path
            logger.info(f"Saved {len(self.server_errors)} server_errors to {file_path}")
        
        if self.validation_errors:
            file_path = os.path.join(self.output_dir, f"validation_errors_{timestamp}.json")
            with open(file_path, 'w') as f:
                json.dump(self.validation_errors, f, indent=2)
            saved_files['validation_errors'] = file_path
            logger.info(f"Saved {len(self.validation_errors)} validation_errors to {file_path}")
        
        if self.slow_responses:
            file_path = os.path.join(self.output_dir, f"slow_responses_{timestamp}.json")
            with open(file_path, 'w') as f:
                json.dump(self.slow_responses, f, indent=2)
            saved_files['slow_responses'] = file_path
            logger.info(f"Saved {len(self.slow_responses)} slow_responses to {file_path}")
        
        if self.timeouts:
            file_path = os.path.join(self.output_dir, f"timeouts_{timestamp}.json")
            with open(file_path, 'w') as f:
                json.dump(self.timeouts, f, indent=2)
            saved_files['timeouts'] = file_path
            logger.info(f"Saved {len(self.timeouts)} timeouts to {file_path}")
        
        if self.sql_injection_hits:
            file_path = os.path.join(self.output_dir, f"sql_injection_{timestamp}.json")
            with open(file_path, 'w') as f:
                json.dump(self.sql_injection_hits, f, indent=2)
            saved_files['sql_injection'] = file_path
            logger.info(f"Saved {len(self.sql_injection_hits)} sql_injection hits to {file_path}")
        
        if self.memory_issues:
            file_path = os.path.join(self.output_dir, f"memory_issues_{timestamp}.json")
            with open(file_path, 'w') as f:
                json.dump(self.memory_issues, f, indent=2)
            saved_files['memory_issues'] = file_path
            logger.info(f"Saved {len(self.memory_issues)} memory_issues to {file_path}")
        
        if self.auth_issues:
            file_path = os.path.join(self.output_dir, f"auth_issues_{timestamp}.json")
            with open(file_path, 'w') as f:
                json.dump(self.auth_issues, f, indent=2)
            saved_files['auth_issues'] = file_path
            logger.info(f"Saved {len(self.auth_issues)} auth_issues to {file_path}")
        
        manifest_path = os.path.join(self.output_dir, "payload_manifest.json")
        with open(manifest_path, 'w') as f:
            json.dump({
                "timestamp": timestamp,
                "files": saved_files,
                "counts": {
                    "high_fitness": len(self.high_fitness_payloads),
                    "server_errors": len(self.server_errors),
                    "validation_errors": len(self.validation_errors),
                    "slow_responses": len(self.slow_responses),
                    "timeouts": len(self.timeouts),
                    "sql_injection_hits": len(self.sql_injection_hits),
                    "memory_issues": len(self.memory_issues),
                    "auth_issues": len(self.auth_issues)
                }
            }, f, indent=2)
        
        with open(os.path.join(self.output_dir, "debug_info.txt"), 'w') as f:
            f.write(f"Timestamp: {timestamp}\n")
            f.write(f"Output directory: {self.output_dir}\n")
            f.write(f"Absolute path: {os.path.abspath(self.output_dir)}\n")
            f.write(f"Files in directory: {os.listdir(self.output_dir)}\n")
        
        return saved_files
    
    def get_statistics(self) -> Dict[str, int]:
        return {
            "high_fitness": len(self.high_fitness_payloads),
            "server_errors": len(self.server_errors),
            "validation_errors": len(self.validation_errors),
            "slow_responses": len(self.slow_responses),
            "timeouts": len(self.timeouts),
            "sql_injection_hits": len(self.sql_injection_hits),
            "memory_issues": len(self.memory_issues),
            "auth_issues": len(self.auth_issues)
        }
    
    def print_summary(self) -> None:
        stats = self.get_statistics()
        
        print("\n=== Payload Tracker Summary ===")
        print(f"Total tracked items: {sum(stats.values())}")
        for category, count in stats.items():
            print(f"  {category}: {count}")
        
        categories_to_show = [
            ("server_errors", self.server_errors),
            ("sql_injection_hits", self.sql_injection_hits),
            ("memory_issues", self.memory_issues)
        ]
        
        print("\n=== Example Findings ===")
        for category_name, items in categories_to_show:
            if items:
                print(f"\n--- {category_name} (showing 1 of {len(items)}) ---")
                example = items[-1]
                print(f"Payload: {json.dumps(example['payload'], indent=2)}")
                print(f"Response status: {example['response'].get('status_code')}")
                
                response_data = example['response'].get('data', {})
                if isinstance(response_data, dict) and 'error' in response_data:
                    print(f"Error: {response_data['error']}")

payload_tracker = PayloadTracker()
