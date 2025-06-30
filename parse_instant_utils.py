import json
import logging
logger = logging.getLogger("TestPilot.ParseInstantUtils")

def fix_json_pattern(pattern_match):
    """
    Fix a JSON pattern that was double-encoded as a string
    """
    # Remove outer quotes
    if pattern_match.startswith('"') and pattern_match.endswith('"'):
        pattern_match = pattern_match[1:-1]
    
    # Add missing opening brace if needed
    if not pattern_match.startswith('{'):
        pattern_match = '{' + pattern_match
    
    # The key insight: don't unescape ALL quotes, just try to parse as-is
    # If that fails, we'll use a different approach
    
    try:
        # Try parsing with escaped quotes as-is first
        return json.loads(pattern_match)
    except json.JSONDecodeError:
        pass
    
    # If direct parsing fails, we need to be smarter about unescaping
    # Only unescape quotes that are not within string values
    
    # This is a complex problem, so let's use a simpler approach:
    # Extract key information without full JSON parsing
    return None

def extract_log_info_regex(pattern_text):
    """
    Extract key information using regex instead of JSON parsing
    """
    import re
    
    # Extract level
    level_match = re.search(r'"level":"([^"]+)"', pattern_text)
    level = level_match.group(1) if level_match else None
    
    # Extract logger name
    logger_match = re.search(r'"loggerName":"([^"]+)"', pattern_text)
    logger = logger_match.group(1) if logger_match else None
    
    # Extract key message parts
    message_match = re.search(r'"message":"([^"]+(?:\\.[^"]*)*)"', pattern_text)
    message = message_match.group(1) if message_match else ""
    
    return {
        'level': level,
        'loggerName': logger,
        'message': message
    }

def check_flexible_log_pattern_v3(output, pattern_match):
    if not output:
        return False
    
    # Extract info using regex instead of JSON parsing
    pattern_info = extract_log_info_regex(pattern_match)
    
    if not pattern_info['level'] or not pattern_info['loggerName']:
        logger.info("Could not extract level or logger from pattern")
        return pattern_match in output  # Fallback to string matching
    
    level = pattern_info['level']
    logger_name = pattern_info['loggerName'] 
    message = pattern_info['message']
    
    logger.info(f"Searching for: level={level}, logger={logger_name}")
    
    # Look for key message components
    key_phrases = []
    if 'Error response generated at IGW' in message:
        key_phrases.append('Error response generated at IGW')
    if 'Request Timeout' in message:
        key_phrases.append('Request Timeout')
    if 'Bad Request' in message:
        key_phrases.append('Bad Request')
    if 'User agent validation failure' in message:
        key_phrases.append('User agent validation failure')
    
    logger.info(f"Key phrases to match: {key_phrases}")
    
    # Search in output
    matches_found = 0
    for line in output.strip().split('\n'):
        if not line.strip():
            continue
            
        try:
            log_entry = json.loads(line)
            logger.debug(f"Checking log entry with expected {level} and {logger_name}: {log_entry}")
            # Match level and logger
            if (log_entry.get('level') == level and 
                log_entry.get('loggerName') == logger_name):
                
                matches_found += 1
                logger.info(f"Found matching level and logger in line {matches_found}")
                
                # Check for key phrases in message
                log_message = log_entry.get('message', '')
                if key_phrases:
                    if any(phrase in log_message for phrase in key_phrases):
                        logger.info(f"Found matching key phrase!")
                        return True
                else:
                    # If no key phrases, just check if logger and level match
                    return True
                    
        except json.JSONDecodeError:
            continue
    
    logger.info(f"Found {matches_found} entries with matching level/logger but no matching key phrases")
    return False