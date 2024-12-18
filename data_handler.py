import os
import json
import zipfile
import sqlite3
import logging
import shutil
import zstandard as zstd
import tempfile
from typing import List, Dict, Any

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_questions(file: Any) -> List[Dict[str, Any]]:
    """
    Load questions from a JSON file or file-like object.

    Parameters
    ----------
    file : Any
        The file path (str) or file-like object to load JSON data from.

    Returns
    -------
    List[Dict[str, Any]]
        A list of dictionaries representing questions.
    """
    if isinstance(file, str):
        # Load from file path
        with open(file, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        # Load from uploaded file-like object
        return json.load(file)

def decompress_anki21b(input_path: str, output_path: str) -> None:
    """
    Decompress a .anki21b file using zstd.

    Parameters
    ----------
    input_path : str
        Path to the compressed .anki21b file.
    output_path : str
        Path where the decompressed SQLite database will be saved.

    Raises
    ------
    Exception
        If decompression fails.
    """
    try:
        with open(input_path, 'rb') as compressed_file:
            dctx = zstd.ZstdDecompressor()
            with open(output_path, 'wb') as output_file:
                dctx.copy_stream(compressed_file, output_file)
        logger.info("Successfully decompressed .anki21b file")
    except Exception as e:
        logger.error(f"Error decompressing .anki21b file: {e}")
        raise

def extract_apkg(apkg_path: str, extract_dir: str) -> str:
    """
    Extract the contents of an Anki package (.apkg) file and return the path to a SQLite database.

    Parameters
    ----------
    apkg_path : str
        Path to the .apkg file.
    extract_dir : str
        Directory where the extracted files will be placed.

    Returns
    -------
    str
        Path to the SQLite database file (collection.sqlite or collection.anki2).

    Raises
    ------
    FileNotFoundError
        If no valid database file is found in the APKG.
    Exception
        If extraction fails.
    """
    try:
        with zipfile.ZipFile(apkg_path, 'r') as zip_ref:
            logger.info(f"Files in APKG archive: {zip_ref.namelist()}")
            zip_ref.extractall(extract_dir)
            
        # Check for collection.anki21b first
        anki21b_path = os.path.join(extract_dir, 'collection.anki21b')
        if os.path.exists(anki21b_path):
            logger.info("Found collection.anki21b")
            # Decompress the .anki21b file
            decompressed_path = os.path.join(extract_dir, 'collection.sqlite')
            decompress_anki21b(anki21b_path, decompressed_path)
            return decompressed_path
            
        # Fall back to collection.anki2
        anki2_path = os.path.join(extract_dir, 'collection.anki2')
        if os.path.exists(anki2_path):
            logger.info("Found collection.anki2")
            return anki2_path
            
        raise FileNotFoundError("No valid database file found in APKG")
    except Exception as e:
        logger.error(f"Error extracting APKG: {e}")
        raise

def convert_apkg_to_json(apkg_path: str) -> List[Dict[str, Any]]:
    """
    Convert an Anki package (.apkg) to a JSON representation.

    Parameters
    ----------
    apkg_path : str
        Path to the .apkg file.

    Returns
    -------
    List[Dict[str, Any]]
        A list of dictionaries representing the converted cards and their data.

    Raises
    ------
    Exception
        If conversion fails.
    """
    extract_dir = os.path.join(os.path.dirname(apkg_path), 'temp_anki_extract')
    os.makedirs(extract_dir, exist_ok=True)
    
    try:
        db_path = extract_apkg(apkg_path, extract_dir)
        logger.info(f"Using database: {db_path}")
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        query = """
        SELECT 
            n.id as note_id,
            n.mid as model_id,
            n.flds as note_fields,
            n.tags,
            c.id as card_id,
            c.type,
            c.queue,
            c.due,
            c.ivl,
            c.factor,
            c.reps,
            c.lapses,
            m.name as model_name
        FROM notes n
        JOIN cards c ON c.nid = n.id
        JOIN notetypes m ON n.mid = m.id
        WHERE c.queue != -1
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        logger.info(f"Found {len(results)} cards")
        
        cards_data = []
        for row in results:
            (note_id, model_id, fields_str, tags, card_id, type_,
             queue, due, interval, factor, reps, lapses, model) = row
            
            fields = fields_str.split('\x1f')
            
            card_data = {
                'note_id': note_id,
                'card_id': card_id,
                'type': type_,
                'queue': queue,
                'due': due,
                'interval': interval,
                'factor': factor,
                'reps': reps,
                'lapses': lapses,
                'model': model,
                'tags': tags.split() if tags else [],
            }
            
            if len(fields) >= 1:
                card_data['Question'] = fields[0]
            if len(fields) >= 2:
                card_data['QType'] = int(fields[1]) if fields[1].isdigit() else 0
            
            for i in range(2, 8):
                if i < len(fields):
                    card_data[f'Q_{i-1}'] = fields[i]
                else:
                    card_data[f'Q_{i-1}'] = ""
            
            if len(fields) >= 9:
                card_data['Answers'] = [fields[8]]
            if len(fields) >= 10:
                card_data['Sources'] = fields[9]
            if len(fields) >= 11:
                card_data['Extra_1'] = fields[10]
            if len(fields) >= 12:
                card_data['Title'] = fields[11]
            
            cards_data.append(card_data)
        
        conn.close()
        
        # Clean up
        try:
            shutil.rmtree(extract_dir)
        except Exception as e:
            logger.warning(f"Error cleaning up temporary files: {e}")
        
        return cards_data
        
    except Exception as e:
        logger.error(f"Error converting APKG to JSON: {e}")
        # Clean up on error
        try:
            shutil.rmtree(extract_dir)
        except Exception as cleanup_error:
            logger.warning(f"Error cleaning up temporary files: {cleanup_error}")
        raise