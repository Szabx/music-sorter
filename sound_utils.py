from pathlib import Path
from typing import Optional, Tuple, Dict
import subprocess
import requests
import musicbrainzngs
import re

def generate_fingerprint(file_path: Path) -> Optional[Tuple[str, int]]:
    """
    Generate AcoustID fingerprint and duration for an audio file.
    :param file_path: Path to the audio file.
    :return: Tuple of fingerprint and duration, or None if fpcalc fails.
    """
    try:
        # Run fpcalc to generate a fingerprint
        result = subprocess.run(["fpcalc", str(file_path)], stdout=subprocess.PIPE, text=True)
        output = result.stdout
        fingerprint, duration = None, None
        for line in output.split("\n"):
            if line.startswith("FINGERPRINT="):
                fingerprint = line.split("=", 1)[1]
            elif line.startswith("DURATION="):
                duration = int(line.split("=", 1)[1])
        return fingerprint, duration
    except FileNotFoundError:
        print("Error: fpcalc not found. Please install Chromaprint.")
        return None
    except Exception as e:
        print(f"Error while generating fingerprint for {file_path}: {e}")
        return None

def recognize_song_acoustid(fingerprint: str, duration: int, api_key: str) -> Optional[Dict]:
    """
    Recognize a song using AcoustID.
    :param fingerprint: AcoustID fingerprint of the audio file.
    :param duration: Duration of the audio file in seconds.
    :param api_key: AcoustID API key.
    :return: JSON response from AcoustID API, or None on failure.
    """
    api_url = "https://api.acoustid.org/v2/lookup"
    params = {
        "client": api_key,
        "format": "json",
        "fingerprint": fingerprint,
        "duration": duration,
        "meta": "recordings"
    }
    try:
        response = requests.get(api_url, params=params)
        response.raise_for_status()  # Raise exception for HTTP errors
        return response.json()
    except requests.RequestException as e:
        print(f"AcoustID API Error: {e}")
        return None

def get_musicbrainz_metadata(recording_id: str, contact_email: str) -> Optional[Dict]:
    """
    Retrieve metadata from MusicBrainz using a recording ID.
    :param recording_id: MusicBrainz recording ID.
    :param contact_email: Contact email for MusicBrainz API user agent.
    :return: Metadata dictionary, or None on failure.
    """
    musicbrainzngs.set_useragent("MusicRecognitionApp", "1.0", contact_email)
    try:
        result = musicbrainzngs.get_recording_by_id(
            recording_id,
            includes=["artist-credits", "release-group-rels", "releases", "tags"]
        )
        return result
    except musicbrainzngs.WebServiceError as e:
        print(f"MusicBrainz API Error for recording ID {recording_id}: {e}")
        return None

def escape_folder_name(name: str) -> str:
    """
    Escape invalid characters in folder names to make them OS-agnostic.
    :param name: Original folder name.
    :return: Sanitized folder name.
    """
    # Replace invalid characters with underscores
    sanitized_name = re.sub(r'[<>:"/\\|?*\n\r\t]', '_', name)  # Regex for invalid characters
    # Strip leading/trailing whitespace and ensure non-empty name
    return sanitized_name.strip() or "unsorted"