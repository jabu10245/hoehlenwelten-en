INPUT_BINARY = "HW.EXE"
OUTPUT_BINARY = "HW_EN.EXE"
ADDRESSES = "addresses.txt"
STRINGS = "strings.txt"

def stringify_bytes(bytes: bytes | bytearray) -> str:
    """Unwraps the bytes representing a string"""
    return stringify_bytesstring(str(bytes))

def stringify_bytesstring(string: str) -> str:
    """Unwraps stringified bytes."""
    if string.startswith("b'") and string.endswith("'"):
        string = string[2:-1]
    elif string.startswith('b"') and string.endswith('"'):
        string = string[2:-1]
    return string

def read_addresses() -> list[tuple[int, int]]:
    """Reads the file with address ranges and returns each one as a tuple
    containing the start and end offset into the original binary.
    """

    addresses: list[tuple[int, int]] = []

    with open(ADDRESSES, 'rt') as file:
        for line in file.readlines():
            # `start` is the offset into the binary where a string block begins, not
            # including the length byte of that first string.
            # `end` is the offset into the binary of the first byte after the last string
            # in a block.
            start, end = [int(s) for s in line.split("-")]
            addresses.append((start, end))
    
    return addresses
            
def read_strings(addresses: list[tuple[int, int]], filename: str) -> list[tuple[int, int, bytearray]]:
    """Reads the string in a binary file of the given name, only considering
    the address ranges containing strings. Returns each one of them as a tuple
    containing the offset into the binary, the string length and the string bytes.
    """
    
    strings: list[tuple[int, int, bytearray]] = []

    try:
        with open(filename, 'rb') as file:
            binary = file.read()
            for start, end in addresses:
                index = start
                while index < end:
                    # The byte in front of the string data is an uint8, which indicates the number
                    # of bytes of the string itself. The string has no zero byte at the end.
                    length = int.from_bytes(binary[index - 1:index], signed=False, byteorder="big")
                    bytes = binary[index:index + length]
                    strings.append((index, length, bytes))
                    index += length + 1
    except FileNotFoundError:
        print(f"File '{filename}' not found, will be generated later.")
    
    return strings

def collect_strings(addresses: list[tuple[int, int]], translations: dict[str, str]) -> list[tuple[int, int, bytearray, bytearray]]:
    """Collects the strings and their previous translations. Returns each one of them as
    a tuple with the offset into the binary, the string length, the original string bytes
    in German, and the translated string bytes in English (or None if not translated yet).
    """
    
    strings_de = read_strings(addresses, filename=INPUT_BINARY)
    strings_en = read_strings(addresses, filename=OUTPUT_BINARY)
    strings: list[tuple[int, int, bytearray, bytearray]] = []

    for index in range(len(strings_de)):
        # get the index (offset), length and bytes of both the German and English versions.
        index_de, length_de, bytes_de = strings_de[index]
        index_en, length_en, bytes_en = strings_en[index] if index < len(strings_en) else [None, None, None]

        # The translation key is the German string, cleaned up. This is the key into the
        # `translations` dictionary.
        translation_key = str(bytes_de)
        translation_key = translation_key[2:-1]

        if length_de == 0 or len(bytes_de) == 0:
            continue # b'' should be skipped.

        # Make sure the indices and lengths match.
        if index_en is not None and index_de != index_en:
            raise RuntimeError(f"Error at index {index}: start addresses don't match (de={index_de}:{bytes_de}, en={index_en}:{bytes_en})")
        if length_en is not None and length_de != length_en:
            raise RuntimeError(f"Error at index {index}: string lengths don't match (de={length_de}:{bytes_de}, en={length_en}:{bytes_en})")
        
        # If we already have a translation (English version) of this string, then use that. Make sure
        # that remaining bytes are filled up with ' ', to make the English string the same length as
        # the German string.
        translation = translations[translation_key] if translation_key in translations else None
        if translation is not None:
            while len(translation) < length_de:
                translation += ' '
            translation_bytes = translation.encode("utf-8")
            if len(translation_bytes) > length_de:
                raise RuntimeError(f"Error at index {index}: translation '{translation}' has {len(translation_bytes)} bytes, (max={length_de})")
            strings.append((index_de, length_de, bytes_de, translation_bytes))
        
        # If the German and English strings are the same, then it isn't translated yet, so we 
        # put None in there.
        elif bytes_en is None or bytes_de == bytes_en:
            strings.append((index_de, length_de, bytes_de, None))
        
        # Otherwise, the English version is translated in the binary, so we use that.
        else:
            strings.append((index_de, length_de, bytes_de, bytes_en))

    return strings

def read_strings_file() -> dict[str, str]:
    """Reads the strings file and returns a dictionary of the translations."""
    
    strings: dict[str, str] = {}

    try:
        with open(STRINGS, 'rt') as file:

            # A block contains either only the German version, or the German and English
            # translation in two lines.
            for block in file.read().split("\n\n"):
                lines = block.split("\n")
                if len(lines) == 2:
                    header, en = lines
                    _, _, de = header.split("\t")
                    de = stringify_bytesstring(de)
                    en = stringify_bytesstring(en)
                    strings[de] = en
    except FileNotFoundError:
        print(f"File '{STRINGS}' not found, will be generated later.")

    return strings

def generate_strings_file(strings: list[tuple[int, int, bytearray, bytearray]]):
    """Generates the updated strings file."""

    string_count = 0
    translation_count = 0
    
    # First remove copies, keep every German string only once.
    unique_strings: list[tuple[str, bytearray]] = []
    for _, _, bytes, _ in strings:
        string = str(bytes)
        string = string[2:-1]
        if not string in [s for s, _ in unique_strings]:
            unique_strings.append((string, bytes))
            string_count += 1
    
    # Then write the strings file.
    with open(STRINGS, 'wt') as file:
        for _, bytes in unique_strings:
            for index, length, de, en in strings:
                if de == bytes and en is not None:
                    translation_count += 1
                    file.write(f"{index}")
                    file.write("\t")
                    file.write(f"{length}")
                    file.write("\t")
                    file.write(str(de))
                    file.write("\n")
                    translation = stringify_bytes(en)
                    file.write(translation)
                    file.write("\n")
                    file.write("\n")
                    break
        for _, bytes in unique_strings:
            for index, length, de, en in strings:
                if de == bytes and en is None:
                    file.write(f"{index}")
                    file.write("\t")
                    file.write(f"{length}")
                    file.write("\t")
                    file.write(str(de))
                    file.write("\n\n")
                    break
    
    translation_ratio = translation_count / string_count
    print(f"{translation_count} of {string_count} strings translated, {translation_ratio * 100:.1f}%")

def generate_translated_binary(strings: list[tuple[int, int, bytearray, bytearray]]):
    """Generates the translated binary."""
    
    # First read the original binary and copy all data into one bigass byte array.
    output = bytearray()
    with open(INPUT_BINARY, 'rb') as file:
        bytes = file.read()
        for byte in bytes:
            output.append(byte)
    
    # Next, replace the bytes with the English translation in that byte array.
    for index, length, _, bytes in strings:
        if bytes is not None and len(bytes) == length:
            output[index:index + length] = bytes
    
    # Finally, write the byte array back into the translated binary file.
    with open(OUTPUT_BINARY, 'wb') as file:
        file.write(output)
    
    print(f"Generated {OUTPUT_BINARY}, {len(output)} bytes.")


translations = read_strings_file()
addresses = read_addresses()
strings = collect_strings(addresses, translations)
generate_strings_file(strings)
generate_translated_binary(strings)
