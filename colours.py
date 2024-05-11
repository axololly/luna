from typing import List, Any

all_colours = {
    'light red': 0xFF968A,
    'solid red': 0xFF0000,
    'light orange': 0xFFC8A2,
    'orange': 0xFFA500,
    'tangerine': 0xFAB128,
    'tiger orange': 0xFC6A03,
    'honey': 0xEC9706,
    'carrot orange': 0xE07117,
    'merigold': 0xFCAE1E,
    'gold': 0xFFD700,
    'light yellow': 0xFFFFB5,
    'light green': 0x77DD77,
    'solid green': 0x00FF00,
    'plant green': 0x008000,
    'deep moss green': 0x30694b,
    'moss green': 0x8A9A5B,
    'baby blue': 0x89CCF0,
    'sky blue': 0x87CEEB,
    'deep sky blue': 0xBFFF,
    'light blue': 0xADD8E6,
    'blue': 0x6488EA,
    'solid blue': 0x0000FF,
    'ocean blue': 0x0047AB,
    'royal blue': 0x4169E1,
    'light diamond': 0xB9F2FF,
    'diamond': 0x70D1F4,
    'diamond blue': 0x4EE2EC,
    'sapphire blue': 0x2554C7,
    'light purple': 0xCBC3E3,
    'light violet': 0xCF9FFF,
    'light lilac': 0xAA98A9,
    'lilac': 0xC8A2C8,
    'grape': 0x6F2DA8,
    'violet': 0xB200ED,
    'pastel violet': 0xD6B4FC,
    'royal purple': 0x7852A9,
    'pink': 0xFFC0CB,
    'light pink': 0xFFB6C1,
    'pastel pink': 0xFFD1DC,
    'bubblegum pink': 0xFFC1CC,
    'neon pink': 0xFF6EC7,
    'bright pink': 0xFF007F,
    'magenta': 0xFF0090,
    'fuchsia': 0xFF00FF,
    'indigo': 0x480082,
    'amethyst': 0x9966CC,
    'black': 0x000000,
    'white': 0xFFFFFF
}

class ColourNotFoundError(Exception):
    pass

class RGB:
    """
    A class to represent a way to store RGB values (eg. RGB(15, 25, 35))
    Mostly just a way to store RGB values with little function in-built.
    Used as a parent for the Colours class.
    """
    def __init__(self, red: int, green: int, blue: int):
        self.red = red
        self.green = green
        self.blue = blue

    def hex_convert(self):
        """
        Convert the instance's RGB values into a hex value.

        Parameters:
        None
        """
        return '0x' + "".join([hex(c).removeprefix('0x').upper() for c in [self.red, self.green, self.blue]])


class Colours(RGB):
    """
    A class that contains methods for retrieving and manipulating colours.
    Child of the RGB class. Some functions can take input as an RGB instance.
    """

    def __init__(self):
        self.all_colours = all_colours

    def chunks(self, iterable: List[Any], size):
        """
        Return a chunked list with a given size.
        
        Parameters:
        - iterable (preferably a list)
        - size (int) (how big each chunk will be)
        """

        for i in range(0, len(iterable), size):
            yield iterable[i:i + size]
    
    def retrieve(self, colour: str | RGB) -> int:
        """
        Retrieves the hex value from a dictionary of predefined colours.

        Parameters:
        - colour (str or RGB instance)
        """

        if (retrieved_colour := all_colours.get(colour.lower(), None)) is None:
            raise ColourNotFoundError(f'Colour "{colour.lower()}" cannot be found in the dictionary.')
        
        return retrieved_colour
        
    def convert(self, colour: str | RGB) -> int:
        """
        Returns a hex code (converted to an integer) of a given string or from an RGB instance.

        Parameters:
        - colour (str or RGB instance)
        """

        if len(colour) not in [6, 7]:
            raise ColourNotFoundError('Length of colour input is passed improperly.')

        elif isinstance(colour, RGB):
            return int(hex(colour.hex_convert()), base = 16)
        
        elif isinstance(colour, str):
            colour.removeprefix('0x')
            colour.removeprefix('#')

            chunks = list(self.chunks(list(colour)))
            raw_code = ["".join([str(s) for s in L]) for L in chunks]
            hex_code = int("".join([hex(c)[2:] for c in raw_code]), base = 16)

            return hex_code

        else:
            raise ColourNotFoundError('Invalid argument passed.')