import argparse
import subprocess
import os
import polib
import xml.etree.ElementTree as ET
from pathlib import Path
import shutil
import textwrap

# Constants
GODOT_REPO_URL = "https://github.com/godotengine/godot.git"
GODOT_DIR = "godot"
DOC_SUBDIR = "doc"
TRANSLATIONS_SUBDIR = "translations"
TRANSLATABLE_XML_TAGS = ['brief_description', 'description', 'member', 'constant']
XML_FILE_EXTENSION = "*.xml"
PO_FILE_EXTENSION = ".po"


def clone_godot_repo(tag):
    """
    Clone Godot repository with specified tag and depth 1.

    Args:
        tag: Git tag to clone
    """
    print(f"\nCloning Godot repository (tag: {tag}, depth: 1)...")

    # Check if godot directory already exists
    if os.path.exists(GODOT_DIR):
        print(f"Directory '{GODOT_DIR}' already exists. Skipping clone.")
        return

    try:
        # Clone with specific tag, depth 1, and single branch
        subprocess.run(
            ["git", "clone", "--branch", tag, "--depth", "1", "--single-branch", 
             GODOT_REPO_URL, GODOT_DIR],
            check=True
        )
        print(f"Successfully cloned Godot repository at tag {tag}")
    except subprocess.CalledProcessError as e:
        print(f"Error cloning repository: {e}")
        exit(1)
    except FileNotFoundError:
        print("Error: git command not found. Please ensure git is installed and in your PATH.")
        exit(1)


def read_translation_file(language_code):
    """
    Read the .po translation file for the specified language.

    Args:
        language_code: Language code (e.g., 'zh_CN', 'en')

    Returns:
        List of translated PO entries
    """
    translations_dir = os.path.join(GODOT_DIR, DOC_SUBDIR, TRANSLATIONS_SUBDIR)
    po_file_path = os.path.join(translations_dir, f"{language_code}{PO_FILE_EXTENSION}")

    print(f"\nReading translation file: {po_file_path}")

    if not os.path.exists(po_file_path):
        _print_translation_file_error(po_file_path, translations_dir)
        exit(1)

    try:
        # Parse .po file using polib
        po_file = polib.pofile(po_file_path)
        _print_translation_statistics(po_file)
        return po_file.translated_entries()
    except Exception as e:
        print(f"Error reading translation file: {e}")
        exit(1)


def _print_translation_file_error(po_file_path, translations_dir):
    """Print error message when translation file is not found."""
    print(f"Error: Translation file '{po_file_path}' not found.")
    print(f"Available files in {translations_dir}:")
    if os.path.exists(translations_dir):
        available_files = [f for f in os.listdir(translations_dir) if f.endswith(PO_FILE_EXTENSION)]
        for file in available_files:
            print(f"  - {file}")


def _print_translation_statistics(po_file):
    """Print statistics about the translation file."""
    print(f"Successfully parsed translation file")
    print(f"  Total entries: {len(po_file)}")
    print(f"  Translated entries: {len(po_file.translated_entries())}")
    print(f"  Untranslated entries: {len(po_file.untranslated_entries())}")
    print(f"  Fuzzy entries: {len(po_file.fuzzy_entries())}")


def create_translation_dict(po_entries):
    """
    Create a dictionary mapping source text to translated text.

    Args:
        po_entries: List of PO entries from translation file

    Returns:
        Dictionary with msgid as key and msgstr as value
    """
    translation_map = {}
    for entry in po_entries:
        # Only include entries with non-empty translations
        if entry.msgstr:
            translation_map[entry.msgid] = entry.msgstr

    return translation_map


def find_xml_files(doc_directory):
    """
    Find all XML files in the documentation directory recursively.

    Args:
        doc_directory: Path to documentation directory

    Returns:
        List of Path objects for all XML files found
    """
    doc_path = Path(doc_directory)

    if not doc_path.exists():
        print(f"Error: Documentation directory '{doc_directory}' not found.")
        return []

    # Use list() for cleaner collection
    xml_files = list(doc_path.rglob(XML_FILE_EXTENSION))
    return xml_files


def extract_common_indentation(text):
    """
    Extract the common indentation from a multi-line text.

    Args:
        text: Multi-line text string

    Returns:
        String containing the common indentation (spaces or tabs)
    """
    non_empty_lines = [line for line in text.splitlines() if line.strip()]
    if not non_empty_lines:
        return ''

    # Get the first non-empty line with original indentation
    first_line_with_indent = non_empty_lines[0]

    # Get the same line after removing common indentation
    dedented_text = textwrap.dedent(text)
    first_line_dedented = next(line for line in dedented_text.splitlines() if line.strip())

    # The difference is the common indentation
    indent_length = len(first_line_with_indent) - len(first_line_dedented)
    common_indent = first_line_with_indent[:indent_length]

    return common_indent


def translate_text(text, translation_map):
    """
    Translate text using the translation map, preserving formatting.

    Args:
        text: Source text to translate
        translation_map: Dictionary mapping source to translated text

    Returns:
        Translated text with preserved formatting, or original if no translation found
    """
    # Return empty or whitespace-only text as-is
    if not text or not text.strip():
        return text

    # Try direct translation first
    if text in translation_map:
        return translation_map[text]

    # Try translation with indentation handling
    stripped_text = text.strip("\n").rstrip()
    placeholder = "__TRANSLATED_TEXT_PLACEHOLDER__"
    text_with_placeholder = text.replace(stripped_text, placeholder)

    common_indent = extract_common_indentation(stripped_text)
    dedented_text = textwrap.dedent(stripped_text)

    if dedented_text in translation_map:
        translated_text = translation_map[dedented_text]
        # Re-apply the original indentation
        translated_text = textwrap.indent(translated_text, common_indent)
        # Restore the original text structure
        translated_text = text_with_placeholder.replace(placeholder, translated_text)
        return translated_text

    # No translation found, return original
    return text


def translate_xml_element(element, translation_map):
    """
    Recursively translate text content in XML elements.

    Args:
        element: XML element to translate
        translation_map: Dictionary mapping source to translated text
    """
    # Translate text content for specific tags
    if element.tag in TRANSLATABLE_XML_TAGS and element.text:
        element.text = translate_text(element.text, translation_map)

    # Recursively process all child elements
    for child in element:
        translate_xml_element(child, translation_map)


def process_xml_file(xml_file_path, translation_map, output_directory):
    """
    Process a single XML file and save the translated version.

    Args:
        xml_file_path: Path to source XML file
        translation_map: Dictionary mapping source to translated text
        output_directory: Directory to save translated file

    Returns:
        True if successful, False otherwise
    """
    try:
        # Parse XML file
        xml_tree = ET.parse(xml_file_path)
        root_element = xml_tree.getroot()

        # Translate all elements recursively
        translate_xml_element(root_element, translation_map)

        # Calculate output path maintaining directory structure
        godot_doc_path = Path(GODOT_DIR) / DOC_SUBDIR
        relative_path = xml_file_path.relative_to(godot_doc_path)
        output_file_path = Path(output_directory) / relative_path

        # Ensure output directory exists
        output_file_path.parent.mkdir(parents=True, exist_ok=True)

        # Save translated XML with UTF-8 encoding
        xml_tree.write(output_file_path, encoding='utf-8', xml_declaration=True)

        return True
    except Exception as e:
        print(f"Error processing {xml_file_path}: {e}")
        return False


def translate_documentation(po_entries, output_directory="translated_doc"):
    """
    Translate all XML documentation files.

    Args:
        po_entries: List of PO entries from translation file
        output_directory: Directory to save translated documentation
    """
    print(f"\nStarting documentation translation...")

    # Create translation map for efficient lookup
    translation_map = create_translation_dict(po_entries)
    print(f"Created translation map with {len(translation_map)} entries")

    # Find all XML files in documentation directory
    doc_directory = os.path.join(GODOT_DIR, DOC_SUBDIR)
    xml_files = find_xml_files(doc_directory)
    print(f"Found {len(xml_files)} XML files to process")

    if not xml_files:
        print("No XML files found to translate.")
        return

    # Ensure output directory exists
    Path(output_directory).mkdir(parents=True, exist_ok=True)

    # Process each XML file with progress tracking
    successful_count = 0
    total_files = len(xml_files)

    for index, xml_file in enumerate(xml_files, 1):
        print(f"Processing [{index}/{total_files}]: {xml_file.name}")
        if process_xml_file(xml_file, translation_map, output_directory):
            successful_count += 1

    # Print summary
    _print_translation_summary(successful_count, total_files, output_directory)


def _print_translation_summary(successful_count, total_count, output_directory):
    """Print summary of translation results."""
    print(f"\nTranslation complete!")
    print(f"  Successfully processed: {successful_count}/{total_count} files")
    print(f"  Output directory: {output_directory}")


def main():
    """Main entry point for Godot documentation translation tool."""
    parser = argparse.ArgumentParser(
        description="Translate Godot documentation using official translation files."
    )
    parser.add_argument(
        "tag", 
        type=str, 
        help="Godot version tag (e.g., '4.0-stable', '3.5.1-stable')"
    )
    parser.add_argument(
        "lang", 
        type=str, 
        help="Language code for translation (e.g., 'zh_CN', 'ja', 'fr')"
    )

    args = parser.parse_args()

    print(f"Godot version tag: {args.tag}")
    print(f"Target language: {args.lang}")

    # Step 1: Clone Godot repository
    clone_godot_repo(args.tag)

    # Step 2: Read translation file
    po_entries = read_translation_file(args.lang)

    # Step 3: Translate documentation
    output_directory = f"translated_doc_{args.lang}"
    translate_documentation(po_entries, output_directory)


if __name__ == "__main__":
    main()
