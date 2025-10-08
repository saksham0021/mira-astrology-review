"""
Astrological JSON Data Parser
Handles parsing of kundli, dosha, and other astrological data from JSON format
"""
import json
import re
from typing import Dict, List, Any, Optional

class AstroDataParser:
    """Parser for astrological JSON data"""
    
    def __init__(self):
        self.dosha_types = [
            'manglik_dosha', 'pitra_dosha', 'kaal_sarp_dosha', 'shani_dosha',
            'rahu_dosha', 'ketu_dosha', 'guru_chandal_dosha', 'angarak_dosha'
        ]
        
    def parse_json_field(self, json_string: str) -> Dict[str, Any]:
        """Parse JSON string and return structured data"""
        if not json_string or json_string.strip() in ['', 'N/A', 'null']:
            return {}
            
        try:
            # Handle both string and already parsed dict
            if isinstance(json_string, dict):
                return json_string
            elif isinstance(json_string, str):
                # Clean up common JSON formatting issues
                cleaned = self._clean_json_string(json_string)
                return json.loads(cleaned)
        except (json.JSONDecodeError, TypeError) as e:
            print(f"JSON parsing error: {e}")
            return self._fallback_parse(json_string)
    
    def _clean_json_string(self, json_str: str) -> str:
        """Clean and fix common JSON formatting issues"""
        # Remove extra whitespace and newlines
        json_str = re.sub(r'\s+', ' ', json_str.strip())
        
        # Fix single quotes to double quotes
        json_str = re.sub(r"'([^']*)':", r'"\1":', json_str)
        json_str = re.sub(r":\s*'([^']*)'", r': "\1"', json_str)
        
        # Handle Python True/False/None
        json_str = re.sub(r'\bTrue\b', 'true', json_str)
        json_str = re.sub(r'\bFalse\b', 'false', json_str)
        json_str = re.sub(r'\bNone\b', 'null', json_str)
        
        return json_str
    
    def _fallback_parse(self, data_string: str) -> Dict[str, Any]:
        """Fallback parser for non-JSON formatted data"""
        result = {}
        
        # Try to extract key-value pairs from string
        patterns = [
            r'(\w+):\s*([^,\n]+)',  # key: value
            r'(\w+)\s*=\s*([^,\n]+)',  # key = value
        ]
        for pattern in patterns:
            matches = re.findall(pattern, data_string)
            for key, value in matches:
                result[key.strip()] = value.strip()
        
        return result
    
    def _extract_dob_from_text(self, text: str) -> Optional[str]:
        """Extract date of birth from text in various formats"""
        if not text:
            return None
        
        # Common date patterns
        date_patterns = [
            # DD/MM/YYYY or DD-MM-YYYY
            r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b',
            # DD Month YYYY (e.g., 15 January 1990, 15 Jan 1990)
            r'\b(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\s+(\d{4})\b',
            # Month DD, YYYY (e.g., January 15, 1990)
            r'\b(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\s+(\d{1,2}),?\s+(\d{4})\b',
            # YYYY-MM-DD (ISO format)
            r'\b(\d{4})[/-](\d{1,2})[/-](\d{1,2})\b',
            # DD.MM.YYYY
            r'\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return None
    
    def parse_kundli_data(self, kundli_json: str) -> Dict[str, Any]:
        """Parse kundli JSON data"""
        kundli_data = self.parse_json_field(kundli_json)
        
        if not kundli_data:
            return self._create_default_kundli()
        
        # Handle array format (like the one seen in DOM)
        if isinstance(kundli_data, list):
            return self._parse_array_kundli(kundli_data)
        
        # Structure kundli data
        basic_info = kundli_data.get('basic_info', {})
        parsed = {
            'basic_info': {
                'ascendant': basic_info.get('ascendant') or kundli_data.get('ascendant', 'N/A'),
                'moon_sign': basic_info.get('moon_sign') or kundli_data.get('moon_sign', 'N/A'),
                'sun_sign': basic_info.get('sun_sign') or kundli_data.get('sun_sign', 'N/A'),
                'birth_nakshatra': basic_info.get('nakshatra') or kundli_data.get('nakshatra', 'N/A')
            },
            'planetary_positions': self._parse_planetary_positions(kundli_data),
            'houses': self._parse_houses(kundli_data),
            'aspects': kundli_data.get('aspects', []),
            'yogas': kundli_data.get('yogas', [])
        }
        
        return parsed
    
    def _parse_array_kundli(self, kundli_array: List) -> Dict[str, Any]:
        """Parse kundli data in array format"""
        houses = {}
        planetary_positions = {}
        
        for i, house_data in enumerate(kundli_array, 1):
            if isinstance(house_data, dict) and 'value' in house_data:
                house_info = house_data['value']
                sign_name = house_info.get('sign_name', f'House {i}')
                planets = house_info.get('planet', [])
                
                # Store house information
                houses[f'house_{i}'] = {
                    'sign': sign_name,
                    'lord': 'N/A',
                    'planets': [p.get('value', '') for p in planets if isinstance(p, dict)]
                }
                
                # Extract planetary positions
                for planet_info in planets:
                    if isinstance(planet_info, dict) and 'value' in planet_info:
                        planet_name = planet_info['value']
                        if planet_name not in planetary_positions:
                            planetary_positions[planet_name] = {
                                'sign': sign_name,
                                'house': str(i),
                                'degree': 'N/A',
                                'retrograde': False
                            }
        
        # Try to determine ascendant (usually house 1)
        ascendant = 'N/A'
        if houses.get('house_1'):
            ascendant = houses['house_1']['sign']
        
        return {
            'basic_info': {
                'ascendant': ascendant,
                'moon_sign': self._find_planet_sign(planetary_positions, 'MOON'),
                'sun_sign': self._find_planet_sign(planetary_positions, 'SUN'),
                'birth_nakshatra': 'N/A'
            },
            'planetary_positions': planetary_positions,
            'houses': houses,
            'aspects': [],
            'yogas': []
        }
    
    def _find_planet_sign(self, positions: Dict, planet_name: str) -> str:
        """Find the sign of a specific planet"""
        for planet, info in positions.items():
            if planet.upper() == planet_name.upper():
                return info.get('sign', 'N/A')
        return 'N/A'
    
    def parse_dosha_data(self, dosha_json: str) -> Dict[str, Any]:
        """Parse comprehensive dosha data"""
        dosha_data = self.parse_json_field(dosha_json)
        
        if not dosha_data:
            return self._create_default_doshas()
        
        parsed_doshas = {}
        
        for dosha_type in self.dosha_types:
            dosha_info = dosha_data.get(dosha_type, {})
            
            if isinstance(dosha_info, str):
                # Simple string format
                parsed_doshas[dosha_type] = {
                    'present': self._determine_dosha_presence(dosha_info),
                    'severity': self._determine_severity(dosha_info),
                    'description': dosha_info,
                    'remedies': []
                }
            elif isinstance(dosha_info, dict):
                # Detailed format
                parsed_doshas[dosha_type] = {
                    'present': dosha_info.get('present', False),
                    'severity': dosha_info.get('severity', 'low'),
                    'description': dosha_info.get('description', ''),
                    'remedies': dosha_info.get('remedies', []),
                    'planets_involved': dosha_info.get('planets', []),
                    'houses_affected': dosha_info.get('houses', [])
                }
        
        return parsed_doshas
    
    def parse_dasha_data(self, dasha_json: str) -> Dict[str, Any]:
        """Parse dasha period data"""
        dasha_data = self.parse_json_field(dasha_json)
        
        if not dasha_data:
            return self._create_default_dasha()
        
        return {
            'current_mahadasha': self._parse_dasha_period(dasha_data.get('mahadasha', {})),
            'current_antardasha': self._parse_dasha_period(dasha_data.get('antardasha', {})),
            'current_pratyantardasha': self._parse_dasha_period(dasha_data.get('pratyantardasha', {})),
            'upcoming_periods': dasha_data.get('upcoming', []),
            'dasha_balance': dasha_data.get('balance', {})
        }
    
    def _parse_planetary_positions(self, kundli_data: Dict) -> Dict[str, Any]:
        """Parse planetary position data"""
        planets = ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn', 'Rahu', 'Ketu']
        positions = {}
        
        planet_data = kundli_data.get('planets', {})
        
        for planet in planets:
            planet_info = planet_data.get(planet, {})
            if isinstance(planet_info, str):
                positions[planet] = {'sign': planet_info, 'degree': 'N/A', 'house': 'N/A'}
            else:
                positions[planet] = {
                    'sign': planet_info.get('sign', 'N/A'),
                    'degree': planet_info.get('degree', 'N/A'),
                    'house': planet_info.get('house', 'N/A'),
                    'retrograde': planet_info.get('retrograde', False)
                }
        
        return positions
    
    def _parse_houses(self, kundli_data: Dict) -> Dict[str, Any]:
        """Parse house information"""
        houses = {}
        house_data = kundli_data.get('houses', {})
        
        for i in range(1, 13):
            house_key = f'house_{i}'
            house_info = house_data.get(str(i), {})
            
            houses[house_key] = {
                'sign': house_info.get('sign', 'N/A'),
                'lord': house_info.get('lord', 'N/A'),
                'planets': house_info.get('planets', [])
            }
        
        return houses
    
    def _parse_dasha_period(self, dasha_info) -> Dict[str, Any]:
        """Parse individual dasha period"""
        if isinstance(dasha_info, str):
            # Try to parse as JSON first
            try:
                json_data = json.loads(dasha_info)
                if isinstance(json_data, dict):
                    return {
                        'planet': json_data.get('planet', 'N/A'),
                        'period': f"{json_data.get('start', 'N/A')} to {json_data.get('end', 'N/A')}",
                        'start_date': json_data.get('start', 'N/A'),
                        'end_date': json_data.get('end', 'N/A'),
                        'planet_id': json_data.get('planet_id', 'N/A')
                    }
            except (json.JSONDecodeError, TypeError):
                pass
            
            # Parse string format like "Venus (2020-2040)"
            match = re.match(r'([^(]+)(?:\s*\(([^)]+)\))?', dasha_info)
            if match:
                return {
                    'planet': match.group(1).strip(),
                    'period': match.group(2).strip() if match.group(2) else 'N/A',
                    'start_date': 'N/A',
                    'end_date': 'N/A'
                }
        elif isinstance(dasha_info, dict):
            return {
                'planet': dasha_info.get('planet', 'N/A'),
                'period': dasha_info.get('period', 'N/A'),
                'start_date': dasha_info.get('start_date', 'N/A'),
                'end_date': dasha_info.get('end_date', 'N/A'),
                'remaining_years': dasha_info.get('remaining_years', 'N/A'),
                'remaining_months': dasha_info.get('remaining_months', 'N/A')
            }
        
        return {
            'planet': 'N/A',
            'period': 'N/A',
            'start_date': 'N/A',
            'end_date': 'N/A'
        }
    
    def _determine_dosha_presence(self, dosha_text: str) -> bool:
        """Determine if dosha is present from text"""
        if not dosha_text or dosha_text.strip() == '' or dosha_text.lower() == 'n/a':
            return False
        
        text_lower = dosha_text.lower().strip()
        
        # Strong negative indicators first
        strong_negative = ['no', 'absent', 'false', 'not found', 'clear', 'not present', 'nil']
        for indicator in strong_negative:
            if text_lower == indicator or text_lower.startswith(indicator + ' ') or text_lower.endswith(' ' + indicator):
                return False
        
        # Strong positive indicators
        positive_indicators = ['yes', 'present', 'true', 'found', 'detected', 'partial', 'mild', 'moderate', 'severe', 'high', 'low', 'medium']
        for indicator in positive_indicators:
            if indicator in text_lower:
                return True
        
        # If text contains meaningful content (not just "no" or empty), assume present
        if len(text_lower) > 3 and text_lower not in ['no', 'nil', 'none']:
            return True
        
        return False  # Default to false if unclear
    
    def _determine_severity(self, dosha_text: str) -> str:
        """Determine dosha severity from text"""
        if not dosha_text:
            return 'low'
        
        text_lower = dosha_text.lower()
        
        if any(word in text_lower for word in ['severe', 'high', 'strong', 'major', 'intense', 'extreme']):
            return 'high'
        elif any(word in text_lower for word in ['moderate', 'medium', 'partial', 'mild']):
            return 'medium'
        elif any(word in text_lower for word in ['yes', 'present', 'found', 'detected']):
            return 'medium'  # Default to medium if present but no severity specified
        else:
            return 'low'
    
    def _create_default_kundli(self) -> Dict[str, Any]:
        """Create default kundli structure"""
        return {
            'basic_info': {
                'ascendant': 'N/A',
                'moon_sign': 'N/A',
                'sun_sign': 'N/A',
                'birth_nakshatra': 'N/A'
            },
            'planetary_positions': {},
            'houses': {},
            'aspects': [],
            'yogas': []
        }
    
    def _create_default_doshas(self) -> Dict[str, Any]:
        """Create default dosha structure"""
        default_doshas = {}
        for dosha_type in self.dosha_types:
            default_doshas[dosha_type] = {
                'present': False,
                'severity': 'low',
                'description': 'N/A',
                'remedies': []
            }
        return default_doshas
    
    def _create_default_dasha(self) -> Dict[str, Any]:
        """Create default dasha structure"""
        return {
            'current_mahadasha': {'planet': 'N/A', 'period': 'N/A'},
            'current_antardasha': {'planet': 'N/A', 'period': 'N/A'},
            'current_pratyantardasha': {'planet': 'N/A', 'period': 'N/A'},
            'upcoming_periods': [],
            'dasha_balance': {}
        }

    def parse_summary_data(self, summary_json: str) -> Dict[str, Any]:
        """Parse summary JSON data containing astrological details"""
        summary_data = self.parse_json_field(summary_json)
        
        if not summary_data:
            return self._create_default_summary()
        
        return {
            'personal_details': {
                'nakshatra': summary_data.get('naksahtra', 'N/A'),  # Note: typo in original data
                'nakshatra_lord': summary_data.get('naksahtralord', 'N/A'),
                'varna': summary_data.get('varna', 'N/A'),
                'paya': summary_data.get('paya', 'N/A'),
                'name_alphabet': summary_data.get('name_alphabet', 'N/A'),
                'tatva': summary_data.get('tatva', 'N/A'),
                'charan': summary_data.get('charan', 'N/A'),
                'gan': summary_data.get('gan', 'N/A')
            },
            'astrological_info': {
                'sign': summary_data.get('sign', 'N/A'),
                'sign_lord': summary_data.get('signlord', 'N/A'),
                'ascendant': summary_data.get('ascendant', 'N/A'),
                'ascendant_lord': summary_data.get('ascendant_lord', 'N/A'),
                'karan': summary_data.get('karan', 'N/A'),
                'yog': summary_data.get('yog', 'N/A'),
                'yunja': summary_data.get('yunja', 'N/A'),
                'tithi': summary_data.get('tithi', 'N/A')
            },
            'additional_info': {
                'vashya': summary_data.get('vashya', 'N/A'),
                'yoni': summary_data.get('yoni', 'N/A'),
                'nadi': summary_data.get('nadi', 'N/A'),
                'moon_sign': summary_data.get('moon_sign', 'N/A'),
                'birth_number': summary_data.get('birth_number', 'N/A'),
                'life_path_number': summary_data.get('life_path_number', 'N/A'),
                'lucky_number': summary_data.get('lucky_number', 'N/A'),
                'lucky_color': summary_data.get('lucky_color', 'N/A'),
                'lucky_day': summary_data.get('lucky_day', 'N/A')
            }
        }
    
    def parse_chat_data(self, chat_json: str) -> Dict[str, Any]:
        """Parse chat JSON data containing user-bot conversations"""
        if not chat_json or chat_json.strip() in ['', 'N/A', 'null']:
            return {'conversations': [], 'summary': 'No chat data available'}
        
        try:
            # Handle malformed JSON with newlines and control characters
            if isinstance(chat_json, str):
                # Clean up the JSON string
                cleaned_json = self._clean_chat_json(chat_json)
                
                # Try to parse as JSON array
                if cleaned_json.strip().startswith('['):
                    chat_data = json.loads(cleaned_json)
                else:
                    # Handle comma-separated JSON objects (not proper array)
                    chat_data = self._parse_comma_separated_json(cleaned_json)
            else:
                chat_data = chat_json
            
            conversations = []
            user_messages = 0
            bot_messages = 0
            
            if isinstance(chat_data, list):
                # Maintain original order from the data
                for i, item in enumerate(chat_data):
                    if isinstance(item, dict):
                        if 'user' in item:
                            conversations.append({
                                'type': 'user',
                                'message': item['user'],
                                'timestamp': item.get('timestamp', 'N/A'),
                                'sequence': i + 1
                            })
                            user_messages += 1
                        elif 'bot' in item:
                            conversations.append({
                                'type': 'bot',
                                'message': item['bot'],
                                'timestamp': item.get('timestamp', 'N/A'),
                                'sequence': i + 1
                            })
                            bot_messages += 1
            
            return {
                'conversations': conversations,  # Keep original order
                'summary': f'{user_messages} user messages, {bot_messages} bot responses',
                'total_messages': len(conversations),
                'user_messages': user_messages,
                'bot_messages': bot_messages
            }
            
        except Exception as e:
            print(f"Error parsing chat data: {e}")
            # Try fallback parsing
            fallback_conversations = self._fallback_chat_parse(chat_json)
            return {
                'conversations': fallback_conversations,
                'summary': f'Fallback parsing: {len(fallback_conversations)} messages',
                'total_messages': len(fallback_conversations),
                'user_messages': sum(1 for c in fallback_conversations if c['type'] == 'user'),
                'bot_messages': sum(1 for c in fallback_conversations if c['type'] == 'bot'),
                'parsing_method': 'fallback'
            }
    
    def _clean_chat_json(self, json_str: str) -> str:
        """Clean chat JSON string to handle control characters and formatting"""
        import re
        
        # Replace problematic control characters
        json_str = json_str.replace('\n', '\\n')
        json_str = json_str.replace('\r', '\\r')
        json_str = json_str.replace('\t', '\\t')
        
        # If it doesn't start with [, try to make it a proper array
        if not json_str.strip().startswith('['):
            # Add array brackets
            json_str = '[' + json_str + ']'
        
        return json_str
    
    def _parse_comma_separated_json(self, json_str: str) -> List[Dict]:
        """Parse comma-separated JSON objects into a list"""
        import re
        
        # Remove array brackets if present
        json_str = json_str.strip()
        if json_str.startswith('[') and json_str.endswith(']'):
            json_str = json_str[1:-1]
        
        # Split by "},{"  pattern to separate objects
        objects = []
        parts = re.split(r'\},\s*\{', json_str)
        
        for i, part in enumerate(parts):
            # Add back the braces
            if i == 0 and not part.startswith('{'):
                part = '{' + part
            if i == len(parts) - 1 and not part.endswith('}'):
                part = part + '}'
            if i > 0 and not part.startswith('{'):
                part = '{' + part
            if i < len(parts) - 1 and not part.endswith('}'):
                part = part + '}'
            
            try:
                obj = json.loads(part)
                objects.append(obj)
            except:
                # Try to extract user/bot content manually
                if '"user"' in part or '"bot"' in part:
                    extracted = self._extract_message_from_text(part)
                    if extracted:
                        objects.append(extracted)
        
        return objects
    
    def _extract_message_from_text(self, text: str) -> Dict:
        """Extract user/bot message from malformed JSON text"""
        import re
        
        # Try to find user message
        user_match = re.search(r'"user":\s*"([^"]*(?:\\.[^"]*)*)"', text)
        if user_match:
            return {'user': user_match.group(1).replace('\\"', '"')}
        
        # Try to find bot message
        bot_match = re.search(r'"bot":\s*"([^"]*(?:\\.[^"]*)*)"', text)
        if bot_match:
            return {'bot': bot_match.group(1).replace('\\"', '"')}
        
        return None
    
    def _fallback_chat_parse(self, chat_text: str) -> List[Dict]:
        """Fallback parsing method for severely malformed chat data"""
        conversations = []
        
        # Use regex to find all user and bot messages
        import re
        
        # Find all user messages
        user_pattern = r'\{"user":\s*"([^"]*(?:\\.[^"]*)*)"[^}]*\}'
        user_matches = re.findall(user_pattern, chat_text)
        
        # Find all bot messages  
        bot_pattern = r'\{"bot":\s*"([^"]*(?:\\.[^"]*)*)"[^}]*\}'
        bot_matches = re.findall(bot_pattern, chat_text)
        
        # Find positions to maintain order
        all_matches = []
        
        for match in re.finditer(user_pattern, chat_text):
            all_matches.append({
                'type': 'user',
                'message': match.group(1).replace('\\n', '\n').replace('\\"', '"'),
                'position': match.start(),
                'sequence': len(all_matches) + 1
            })
        
        for match in re.finditer(bot_pattern, chat_text):
            all_matches.append({
                'type': 'bot', 
                'message': match.group(1).replace('\\n', '\n').replace('\\"', '"'),
                'position': match.start(),
                'sequence': len(all_matches) + 1
            })
        
        # Sort by position to maintain chronological order
        all_matches.sort(key=lambda x: x['position'])
        
        # Remove position info and add proper sequence numbers
        for i, match in enumerate(all_matches):
            conversations.append({
                'type': match['type'],
                'message': match['message'],
                'timestamp': 'N/A',
                'sequence': i + 1
            })
        
        return conversations
    
    def _extract_conversations_from_text(self, text: str) -> List[Dict]:
        """Extract conversations from malformed JSON text"""
        conversations = []
        
        # Try to find user and bot messages using regex
        user_pattern = r'"user":\s*"([^"]*)"'
        bot_pattern = r'"bot":\s*"([^"]*)"'
        
        user_matches = re.findall(user_pattern, text)
        bot_matches = re.findall(bot_pattern, text)
        
        for msg in user_matches:
            conversations.append({'user': msg})
        
        for msg in bot_matches:
            conversations.append({'bot': msg})
        
        return conversations
    
    def _create_default_summary(self) -> Dict[str, Any]:
        """Create default summary structure"""
        return {
            'personal_details': {
                'nakshatra': 'N/A',
                'nakshatra_lord': 'N/A',
                'varna': 'N/A',
                'paya': 'N/A',
                'name_alphabet': 'N/A',
                'tatva': 'N/A',
                'charan': 'N/A',
                'gan': 'N/A'
            },
            'astrological_info': {
                'sign': 'N/A',
                'sign_lord': 'N/A',
                'ascendant': 'N/A',
                'ascendant_lord': 'N/A',
                'karan': 'N/A',
                'yog': 'N/A',
                'yunja': 'N/A',
                'tithi': 'N/A'
            },
            'additional_info': {
                'vashya': 'N/A',
                'yoni': 'N/A',
                'nadi': 'N/A',
                'moon_sign': 'N/A',
                'birth_number': 'N/A',
                'life_path_number': 'N/A',
                'lucky_number': 'N/A',
                'lucky_color': 'N/A',
                'lucky_day': 'N/A'
            }
        }

# Utility functions for integration
def parse_session_astrological_data(session_data: Dict[str, Any]) -> Dict[str, Any]:
    """Parse all astrological data for a session"""
    parser = AstroDataParser()
    
    # Try to use JSON data first, fallback to text fields
    kundli_source = session_data.get('kundli_json') or session_data.get('kundli', '')
    dosha_source = session_data.get('dosha_json', '')
    
    # If no JSON dosha data, create from individual fields
    if not dosha_source or dosha_source.strip() == '':
        dosha_source = json.dumps({
            'manglik_dosha': {
                'present': parser._determine_dosha_presence(session_data.get('manglik_dosha', '')),
                'severity': parser._determine_severity(session_data.get('manglik_dosha', '')),
                'description': session_data.get('manglik_dosha', 'N/A'),
                'remedies': []
            },
            'pitra_dosha': {
                'present': parser._determine_dosha_presence(session_data.get('pitra_dosha', '')),
                'severity': parser._determine_severity(session_data.get('pitra_dosha', '')),
                'description': session_data.get('pitra_dosha', 'N/A'),
                'remedies': []
            }
        })
    
    result = {
        'kundli': parser.parse_kundli_data(kundli_source),
        'doshas': parser.parse_dosha_data(dosha_source),
        'dasha': {
            'major': parser._parse_dasha_period(session_data.get('major_dasha', '')),
            'minor': parser._parse_dasha_period(session_data.get('minor_dasha', '')),
            'sub_minor': parser._parse_dasha_period(session_data.get('sub_minor_dasha', ''))
        },
        'summary': parser.parse_summary_data(session_data.get('summary', '')),
        'chat': parser.parse_chat_data(session_data.get('chat', ''))
    }
    
    return result
