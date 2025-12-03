import argparse
import subprocess
import os
import polib
import xml.etree.ElementTree as ET
from pathlib import Path
import shutil
import textwrap


def clone_godot_repo(tag):
    """Clone Godot repository with specified tag and depth 1."""
    godot_repo_url = "https://github.com/godotengine/godot.git"
    godot_dir = "godot"

    print(f"\nCloning Godot repository (tag: {tag}, depth: 1)...")

    try:
        # Check if godot directory already exists
        if os.path.exists(godot_dir):
            print(f"Directory '{godot_dir}' already exists. Skipping clone.")
        else:
            # Clone with specific tag, depth 1, and single branch
            subprocess.run(
                ["git", "clone", "--branch", tag, "--depth", "1", "--single-branch", godot_repo_url, godot_dir],
                check=True
            )
            print(f"Successfully cloned Godot repository at tag {tag}")
    except subprocess.CalledProcessError as e:
        print(f"Error cloning repository: {e}")
        exit(1)
    except FileNotFoundError:
        print("Error: git command not found. Please ensure git is installed and in your PATH.")
        exit(1)


def read_translation_file(lang):
    """Read the .po file for the specified language from godot/doc/translations/ using polib."""
    translations_dir = os.path.join("godot", "doc", "translations")
    po_file_path = os.path.join(translations_dir, f"{lang}.po")

    print(f"\nReading translation file: {po_file_path}")

    try:
        if not os.path.exists(po_file_path):
            print(f"Error: Translation file '{po_file_path}' not found.")
            print(f"Available files in {translations_dir}:")
            if os.path.exists(translations_dir):
                files = [f for f in os.listdir(translations_dir) if f.endswith('.po')]
                for f in files:
                    print(f"  - {f}")
            exit(1)

        # Parse .po file using polib
        po = polib.pofile(po_file_path)

        print(f"Successfully parsed translation file")
        print(f"  Total entries: {len(po)}")
        print(f"  Translated entries: {len(po.translated_entries())}")
        print(f"  Untranslated entries: {len(po.untranslated_entries())}")
        print(f"  Fuzzy entries: {len(po.fuzzy_entries())}")

        return po.translated_entries()
    except Exception as e:
        print(f"Error reading translation file: {e}")
        exit(1)


def create_translation_dict(po_entries):
    """Create a dictionary from po entries for faster lookup."""
    translation_dict = {}
    for entry in po_entries:
        if entry.msgstr:  # Only include entries with translations
            translation_dict[entry.msgid] = entry.msgstr

    return translation_dict


def find_xml_files(doc_dir):
    """Find all XML files in the doc directory."""
    xml_files = []
    doc_path = Path(doc_dir)

    if not doc_path.exists():
        print(f"Error: Documentation directory '{doc_dir}' not found.")
        return xml_files

    for xml_file in doc_path.rglob("*.xml"):
        xml_files.append(xml_file)

    return xml_files


def get_common_indent(text):
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return ''

    original = lines[0]  # 原始第一个非空行
    dedent = textwrap.dedent(text)
    dedent_line = next(line for line in dedent.splitlines() if line.strip())

    # 差异就是共同缩进
    indent = original[:len(original) - len(dedent_line)]
    return indent


def translate_text(text, translation_dict):
    if not text or not text.strip():
        return text

    if text in translation_dict:
        return translation_dict[text]

    # Extract common indentation
    text_stripped = text.strip("\n").rstrip()
    text_placeholder = "__TRANSLATED_TEXT_PLACEHOLDER__"
    text_wrapper = text.replace(text_stripped, text_placeholder)

    indent = get_common_indent(text_stripped)
    text_cleared = textwrap.dedent(text_stripped)

    if text_cleared in translation_dict:
        translated = translation_dict[text_cleared]
        translated = textwrap.indent(translated, indent)
        translated = text_wrapper.replace(text_placeholder, translated)
        return translated

    return text


def translate_xml_element(element, translation_dict):
    tag_list = ['brief_description', 'description', 'member', 'constant']

    if element.tag in tag_list and element.text:
        element.text = translate_text(element.text, translation_dict)

    # Recursively process children
    for child in element:
        translate_xml_element(child, translation_dict)


def process_xml_file(xml_file_path, translation_dict, output_dir):
    """Process a single XML file and save the translated version."""
    try:
        # Parse XML file
        tree = ET.parse(xml_file_path)
        root = tree.getroot()

        # Translate all elements
        translate_xml_element(root, translation_dict)

        # Calculate relative path and create output path
        relative_path = xml_file_path.relative_to("godot/doc")
        output_path = Path(output_dir) / relative_path

        # Create output directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Save translated XML
        tree.write(output_path, encoding='utf-8', xml_declaration=True)

        return True
    except Exception as e:
        print(f"Error processing {xml_file_path}: {e}")
        return False


def translate_documentation(po_entries, output_dir="translated_doc"):
    """Translate all XML files in godot/doc directory."""
    print(f"\nStarting documentation translation...")

    # Create translation dictionary for faster lookup
    translation_dict = create_translation_dict(po_entries)
    print(f"Created translation dictionary with {len(translation_dict)} entries")

    # Find all XML files
    doc_dir = os.path.join("godot", "doc")
    xml_files = find_xml_files(doc_dir)
    print(f"Found {len(xml_files)} XML files to process")

    if not xml_files:
        print("No XML files found to translate.")
        return

    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Process each XML file
    success_count = 0
    for i, xml_file in enumerate(xml_files, 1):
        print(f"Processing [{i}/{len(xml_files)}]: {xml_file.name}")
        if process_xml_file(xml_file, translation_dict, output_dir):
            success_count += 1

    print(f"\nTranslation complete!")
    print(f"  Successfully processed: {success_count}/{len(xml_files)} files")
    print(f"  Output directory: {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Process tag and lang arguments.")
    parser.add_argument("tag", type=str, help="The tag argument")
    parser.add_argument("lang", type=str, help="The language argument")

    args = parser.parse_args()

    print(f"Tag: {args.tag}")
    print(f"Lang: {args.lang}")

    clone_godot_repo(args.tag)
    po_entries = read_translation_file(args.lang)

    # Translate documentation and output to new folder
    output_dir = f"translated_doc_{args.lang}"
    translate_documentation(po_entries, output_dir)


if __name__ == "__main__":
    main()
