"""
Kundli Chart Generator
Creates visual representation of birth chart from JSON data
"""
from PIL import Image, ImageDraw, ImageFont
import json
import io


def generate_kundli_image(kundli_json_str):
    """
    Generate a traditional North Indian style kundli chart
    Returns: PIL Image object
    """
    try:
        # Check if data is in text format instead of JSON
        if not kundli_json_str.strip().startswith('['):
            # Return error image for text format
            img = Image.new('RGB', (1000, 1000), '#ffffff')
            draw = ImageDraw.Draw(img)
            try:
                font_error = ImageFont.truetype("arial.ttf", 32)
            except:
                font_error = ImageFont.load_default()
            
            # Draw error message
            error_msg = "Kundli data is in text format.\nChart visualization requires JSON format."
            draw.text((500, 400), error_msg, fill='#d32f2f', anchor="mm", font=font_error)
            
            # Draw the text data below
            try:
                font_text = ImageFont.truetype("arial.ttf", 20)
            except:
                font_text = ImageFont.load_default()
            
            lines = kundli_json_str.strip().split('\n')[:15]  # First 15 lines
            y_pos = 500
            for line in lines:
                draw.text((500, y_pos), line.strip(), fill='#000000', anchor="mm", font=font_text)
                y_pos += 25
            
            return img
        
        # Parse kundli data
        kundli_data = json.loads(kundli_json_str)
        
        # Create larger image for better readability
        img_size = 1000
        img = Image.new('RGB', (img_size, img_size), '#ffffff')
        draw = ImageDraw.Draw(img)
        
        # Try to load fonts - increased sizes for better mobile readability
        try:
            font_title = ImageFont.truetype("arial.ttf", 40)
            font_house = ImageFont.truetype("arialbd.ttf", 28)
            font_planet = ImageFont.truetype("arialbd.ttf", 34)
            font_sign = ImageFont.truetype("arial.ttf", 24)
        except:
            font_title = ImageFont.load_default()
            font_house = ImageFont.load_default()
            font_planet = ImageFont.load_default()
            font_sign = ImageFont.load_default()
        
        # Professional color scheme
        border_color = '#000000'
        bg_color = '#fffef7'
        text_color = '#000000'
        planet_color = '#d32f2f'
        house_bg = '#e8f5e9'
        sign_color = '#1976d2'
        
        # Draw background
        margin = 100
        chart_size = img_size - (2 * margin)
        
        # Calculate center
        center_x = img_size // 2
        center_y = img_size // 2
        
        # North Indian Style - Diamond pattern inside square
        # Define square corners
        top_left = (margin, margin)
        top_right = (img_size - margin, margin)
        bottom_right = (img_size - margin, img_size - margin)
        bottom_left = (margin, img_size - margin)
        
        # Draw outer square
        draw.rectangle([margin, margin, img_size - margin, img_size - margin], 
                      fill=bg_color, outline=border_color, width=4)
        
        # Calculate diamond points (midpoints of square sides)
        top_mid = (center_x, margin)
        right_mid = (img_size - margin, center_y)
        bottom_mid = (center_x, img_size - margin)
        left_mid = (margin, center_y)
        
        # Draw the inner diamond (connects midpoints)
        diamond = [top_mid, right_mid, bottom_mid, left_mid, top_mid]
        draw.line(diamond, fill=border_color, width=3)
        
        # Draw diagonals from corners to opposite corners (creates X pattern)
        draw.line([top_left, bottom_right], fill=border_color, width=3)
        draw.line([top_right, bottom_left], fill=border_color, width=3)
        
        # Draw lines from diamond corners to square corners
        # Top diamond point to top corners
        draw.line([top_mid, top_left], fill=border_color, width=3)
        draw.line([top_mid, top_right], fill=border_color, width=3)
        
        # Right diamond point to right corners
        draw.line([right_mid, top_right], fill=border_color, width=3)
        draw.line([right_mid, bottom_right], fill=border_color, width=3)
        
        # Bottom diamond point to bottom corners
        draw.line([bottom_mid, bottom_right], fill=border_color, width=3)
        draw.line([bottom_mid, bottom_left], fill=border_color, width=3)
        
        # Left diamond point to left corners
        draw.line([left_mid, bottom_left], fill=border_color, width=3)
        draw.line([left_mid, top_left], fill=border_color, width=3)
        
        # Extract planetary positions
        houses = {}
        for idx, house_data in enumerate(kundli_data, 1):
            if 'value' in house_data:
                value = house_data['value']
                sign_name = value.get('sign_name', '')
                planets = value.get('planet', [])
                
                planet_names = []
                for planet in planets:
                    if 'value' in planet:
                        planet_names.append(planet['value'])
                
                houses[idx] = {
                    'sign': sign_name,
                    'planets': planet_names
                }
        
        # House positions matching the exact North Indian format
        # Carefully positioned to center content in each triangular house
        
        house_positions = {
            # Top row (houses 2, 1, 12)
            2: (center_x - 200, margin + 80),           # Top-left triangle
            1: (center_x, margin + 150),                # Top-center triangle (Ascendant) - lowered more
            12: (center_x + 200, margin + 80),          # Top-right triangle
            
            # Left side (houses 3, 4, 5)
            3: (margin + 60, center_y - 150),           # Left-top triangle
            4: (margin + 150, center_y),                # Left-center triangle - moved right
            5: (margin + 60, center_y + 180),           # Left-bottom triangle - lowered
            
            # Bottom row (houses 6, 7, 8)
            6: (center_x - 200, img_size - margin - 80), # Bottom-left triangle
            7: (center_x, img_size - margin - 150),      # Bottom-center triangle - lifted more
            8: (center_x + 200, img_size - margin - 80), # Bottom-right triangle
            
            # Right side (houses 9, 10, 11)
            9: (img_size - margin - 60, center_y + 200), # Right-bottom triangle - lowered more
            10: (img_size - margin - 150, center_y),     # Right-center triangle - moved left
            11: (img_size - margin - 60, center_y - 150),# Right-top triangle
        }
        
        # Draw house numbers and content - properly aligned in each triangle
        for house_num, pos in house_positions.items():
            x, y = pos
            
            # Draw house number (small, in top-left of each house)
            house_text = f"{house_num}"
            draw.text((x - 40, y - 40), house_text, fill=text_color, font=font_house, anchor="mm")
            
            # Prepare content to display
            content_lines = []
            
            # Add sign name if available
            if house_num in houses and houses[house_num]['sign']:
                sign_name = houses[house_num]['sign'][:3]  # Abbreviate (Ari, Tau, etc.)
                content_lines.append((sign_name, sign_color, font_sign))
            
            # Add planets if any
            if house_num in houses and houses[house_num]['planets']:
                planets_list = houses[house_num]['planets']
                
                # Abbreviate planet names
                planet_abbr = []
                for p in planets_list:
                    if p == 'SUN': planet_abbr.append('Su')
                    elif p == 'MOON': planet_abbr.append('Mo')
                    elif p == 'MARS': planet_abbr.append('Ma')
                    elif p == 'MERCURY': planet_abbr.append('Me')
                    elif p == 'JUPITER': planet_abbr.append('Ju')
                    elif p == 'VENUS': planet_abbr.append('Ve')
                    elif p == 'SATURN': planet_abbr.append('Sa')
                    elif p == 'RAHU': planet_abbr.append('Ra')
                    elif p == 'KETU': planet_abbr.append('Ke')
                    else: planet_abbr.append(p[:2])
                
                # Add planets (max 2 per line)
                for i in range(0, len(planet_abbr), 2):
                    line = ' '.join(planet_abbr[i:i+2])
                    content_lines.append((line, planet_color, font_planet))
            
            # Draw all content centered vertically
            total_lines = len(content_lines)
            if total_lines > 0:
                start_y = y - (total_lines * 15) // 2
                for idx, (text, color, font) in enumerate(content_lines):
                    draw.text((x, start_y + idx * 25), text, fill=color, font=font, anchor="mm")
        
        # Add ascendant marker at top
        asc_text = "↑ Ascendant (Lagna)"
        draw.text((center_x, 20), asc_text, fill=planet_color, font=font_house, anchor="mm")
        
        # Add title
        title_y = 50
        title_text = "BIRTH CHART (KUNDLI)"
        draw.text((center_x, title_y), title_text, fill=border_color, font=font_title, anchor="mm")
        
        # Add planet legend at bottom
        legend_y = img_size - 50
        legend_text = "Su=Sun  Mo=Moon  Ma=Mars  Me=Mercury  Ju=Jupiter  Ve=Venus  Sa=Saturn  Ra=Rahu  Ke=Ketu"
        draw.text((center_x, legend_y), legend_text, fill=text_color, font=font_sign, anchor="mm")
        
        # Add style indicator
        style_y = img_size - 30
        draw.text((center_x, style_y), "North Indian Style", fill=sign_color, font=font_sign, anchor="mm")
        
        return img
        
    except Exception as e:
        # Return error image with better formatting
        img = Image.new('RGB', (1000, 1000), '#ffffff')
        draw = ImageDraw.Draw(img)
        try:
            font_error = ImageFont.truetype("arial.ttf", 28)
        except:
            font_error = ImageFont.load_default()
        
        error_text = f"Error generating kundli chart:\n\n{str(e)}"
        draw.text((500, 500), error_text, fill='#d32f2f', anchor="mm", font=font_error)
        return img


def kundli_to_bytes(kundli_json_str):
    """Convert kundli JSON to image bytes"""
    img = generate_kundli_image(kundli_json_str)
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return img_bytes


def generate_kundli_from_parsed_data(parsed_kundli):
    """
    Generate kundli chart from already parsed kundli data
    """
    try:
        # Convert parsed data back to array format for chart generation
        houses_data = []
        
        # Get houses from parsed data
        houses = parsed_kundli.get('houses', {})
        
        for i in range(1, 13):
            house_key = f'house_{i}'
            house_info = houses.get(house_key, {})
            
            # Get sign name
            sign_name = house_info.get('sign', 'N/A')
            
            # Get planets in this house
            planets_in_house = []
            for planet_name in house_info.get('planets', []):
                planets_in_house.append({'value': planet_name})
            
            house_data = {
                'value': {
                    'sign_name': sign_name,
                    'planet': planets_in_house,
                    'sign': i
                }
            }
            houses_data.append(house_data)
        
        # Convert to JSON string and generate image
        json_str = json.dumps(houses_data)
        return generate_kundli_image(json_str)
        
    except Exception as e:
        # Return error image
        img = Image.new('RGB', (1000, 1000), '#ffffff')
        draw = ImageDraw.Draw(img)
        try:
            font_error = ImageFont.truetype("arial.ttf", 28)
        except:
            font_error = ImageFont.load_default()
        
        error_text = f"Error generating chart from parsed data:\n\n{str(e)}"
        draw.text((500, 500), error_text, fill='#d32f2f', anchor="mm", font=font_error)
        return img
