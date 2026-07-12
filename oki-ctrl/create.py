from PIL import Image, ImageDraw, ImageChops

def generate_moire_pattern(size=480, spacing=10, angle_offset=10, line_color=(0, 0, 0), bg_color=(255, 255, 255)):
    """
    Generate a moiré pattern by drawing two layers of lines at different angles.
    
    Parameters:
      - size: The width and height of the image in pixels.
      - spacing: The distance between lines.
      - angle_offset: The angle (in degrees) to rotate the second layer.
      - line_color: RGB tuple for the line color.
      - bg_color: RGB tuple for the background color.
      
    Returns:
      - A PIL Image object containing the generated moiré pattern.
    """
    # Create two layers with a solid background
    layer1 = Image.new("RGB", (size, size), bg_color)
    layer2 = Image.new("RGB", (size, size), bg_color)
    
    draw1 = ImageDraw.Draw(layer1)
    draw2 = ImageDraw.Draw(layer2)
    
    # Draw vertical lines on the first layer
    for x in range(-size, size * 2, spacing):
        draw1.line([(x, 0), (x, size)], fill=line_color, width=1)
    
    # Draw vertical lines on the second layer (will rotate later)
    for x in range(-size, size * 2, spacing):
        draw2.line([(x, 0), (x, size)], fill=line_color, width=1)
    
    # Rotate the second layer to create the moiré effect
    layer2 = layer2.rotate(angle_offset, resample=Image.BICUBIC, expand=False)
    
    # Combine both layers using a blend mode (darker works well for moiré)
    combined = ImageChops.darker(layer1, layer2)
    
    return combined

if __name__ == "__main__":
    # Customization options
    image_size = 480
    line_spacing = 8        # Adjust spacing between lines
    rotation_angle = 15     # Adjust rotation angle for the second layer
    color_lines = (0, 0, 0) # Black lines
    color_background = (255, 255, 255) # White background
    
    # Generate the pattern
    img = generate_moire_pattern(
        size=image_size,
        spacing=line_spacing,
        angle_offset=rotation_angle,
        line_color=color_lines,
        bg_color=color_background
    )
    
    # Save the image as a BMP file
    img.save("moire_pattern.bmp")
    print("Moire pattern saved as 'moire_pattern.bmp'.")
